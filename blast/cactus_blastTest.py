#!/usr/bin/env python

#Copyright (C) 2009-2011 by Benedict Paten (benedictpaten@gmail.com)
#
#Released under the MIT license, see LICENSE.txt
import unittest
import os
import sys
import random
import time

from sonLib.bioio import system
from sonLib.bioio import logger
from sonLib.bioio import fastaWrite
from sonLib.bioio import getRandomSequence
from sonLib.bioio import mutateSequence
from sonLib.bioio import reverseComplement
from sonLib.bioio import getTempFile
from sonLib.bioio import getTempDirectory
from sonLib.bioio import cigarRead
from sonLib.bioio import PairwiseAlignment
from sonLib.bioio import getLogLevelString
from sonLib.bioio import TestStatus
from sonLib.bioio import catFiles
from cactus.shared.test import parseCactusSuiteTestOptions
from cactus.shared.common import runCactusBlast
from cactus.blast.cactus_blast import decompressFastaFile, compressFastaFile

from jobTree.src.common import runJobTreeStatusAndFailIfNotComplete

class TestCase(unittest.TestCase):
    def setUp(self):
        self.testNo = TestStatus.getTestSetup(1, 5, 10, 100)
        self.tempDir = getTempDirectory(os.getcwd())
        self.tempFiles = []
        unittest.TestCase.setUp(self)
        self.tempOutputFile = os.path.join(self.tempDir, "results1.txt")
        self.tempFiles.append(self.tempOutputFile)
        self.tempOutputFile2 = os.path.join(self.tempDir, "results2.txt")
        self.tempFiles.append(self.tempOutputFile2) 
        self.encodePath = os.path.join(TestStatus.getPathToDataSets(), "MAY-2005")
    
    def tearDown(self):
        for tempFile in self.tempFiles:
            if os.path.exists(tempFile):
                os.remove(tempFile)
        unittest.TestCase.tearDown(self)
        system("rm -rf %s" % self.tempDir)
        
    def testBlastEncode(self):
        """For each encode region, for set of pairwise species, run 
        cactus_blast.py. We compare the output with a naive run of the blast program, to check the results are nearly
        equivalent.
        """
        encodeRegions = [ "ENm00" + str(i) for i in xrange(1,2) ] #, 2) ] #Could go to six
        species = ("human", "mouse", "dog")
        #Other species to try "rat", "monodelphis", "macaque", "chimp"
        for encodeRegion in encodeRegions:
            regionPath = os.path.join(self.encodePath, encodeRegion)
            for i in xrange(len(species)):
                species1 = species[i]
                for species2 in species[i+1:]:
                    seqFile1 = os.path.join(regionPath, "%s.%s.fa" % (species1, encodeRegion))
                    seqFile2 = os.path.join(regionPath, "%s.%s.fa" % (species2, encodeRegion))
                    
                    #Run the random
                    runNaiveBlast(seqFile1, seqFile2, self.tempOutputFile)
                    logger.info("Ran the naive blast okay")
                    
                    #Run the blast
                    jobTreeDir = os.path.join(getTempDirectory(self.tempDir), "jobTree")
                    runCactusBlast([ seqFile1, seqFile2 ], self.tempOutputFile2, jobTreeDir,
                                   chunkSize=500000, overlapSize=10000)
                    runJobTreeStatusAndFailIfNotComplete(jobTreeDir)
                    system("rm -rf %s " % jobTreeDir)    
                    logger.info("Ran cactus_blast okay")
                    
                    logger.critical("Comparing cactus_blast and naive blast")
                    compareResultsFile(self.tempOutputFile, self.tempOutputFile2)
    
    def testBlastParameters(self):
        """Tests if changing parameters of lastz creates results similar to the desired default.
        """
        encodeRegion = "ENm001"
        species = ("human", "mouse", "dog")
        #Other species to try "rat", "monodelphis", "macaque", "chimp"
        regionPath = os.path.join(self.encodePath, encodeRegion)
        for i in xrange(len(species)):
            species1 = species[i]
            for species2 in species[i+1:]:
                seqFile1 = os.path.join(regionPath, "%s.%s.fa" % (species1, encodeRegion))
                seqFile2 = os.path.join(regionPath, "%s.%s.fa" % (species2, encodeRegion))
                
                #Run the random
                runNaiveBlast(seqFile1, seqFile2, self.tempOutputFile2,
                              lastzOptions="--nogapped --hspthresh=3000 --ambiguous=iupac")
                #Run the blast
                runNaiveBlast(seqFile1, seqFile2, self.tempOutputFile, 
                              lastzOptions="--nogapped --step=3 --hspthresh=3000 --ambiguous=iupac")
                
                logger.critical("Comparing blast settings")
                compareResultsFile(self.tempOutputFile, self.tempOutputFile2, 0.7)
    
    def testBlastRandom(self):
        """Make some sequences, put them in a file, call blast with random parameters 
        and check it runs okay.
        """
        tempSeqFile = os.path.join(self.tempDir, "tempSeq.fa")
        self.tempFiles.append(tempSeqFile)
        for test in xrange(self.testNo):
            seqNo = random.choice(xrange(0, 10))
            seq = getRandomSequence(8000)[1]
            fileHandle = open(tempSeqFile, 'w')
            for fastaHeader, seq in [ (str(i), mutateSequence(seq, 0.3*random.random())) for i in xrange(seqNo) ]:
                if random.random() > 0.5:
                    seq = reverseComplement(seq)
                fastaWrite(fileHandle, fastaHeader, seq)
            fileHandle.close()
            chunkSize = random.choice(xrange(500, 9000))
            overlapSize = random.choice(xrange(2, 100))
            jobTreeDir = os.path.join(getTempDirectory(self.tempDir), "jobTree")
            runCactusBlast([ tempSeqFile ], self.tempOutputFile, jobTreeDir, chunkSize, overlapSize)
            runJobTreeStatusAndFailIfNotComplete(jobTreeDir)
            if getLogLevelString() == "DEBUG":
                system("cat %s" % self.tempOutputFile)
            system("rm -rf %s " % jobTreeDir)
            
    def testCompression(self):
        tempSeqFile = os.path.join(self.tempDir, "tempSeq.fa")
        tempSeqFile2 = os.path.join(self.tempDir, "tempSeq2.fa")
        self.tempFiles.append(tempSeqFile)
        self.tempFiles.append(tempSeqFile2)
        self.encodePath = os.path.join(self.encodePath, "ENm001")
        catFiles([ os.path.join(self.encodePath, fileName) for fileName in os.listdir(self.encodePath) ], tempSeqFile)
        startTime = time.time()
        compressFastaFile(tempSeqFile)
        logger.critical("It took %s seconds to compress the fasta file" % (time.time() - startTime))
        startTime = time.time()
        system("rm %s" % tempSeqFile + ".bz2")
        system("bzip2 --keep --fast %s" % tempSeqFile)
        logger.critical("It took %s seconds to compress the fasta file by system functions" % (time.time() - startTime))
        startTime = time.time()
        decompressFastaFile(tempSeqFile + ".bz2", tempSeqFile2)
        logger.critical("It took %s seconds to decompress the fasta file" % (time.time() - startTime))
        system("rm %s" % tempSeqFile2)
        startTime = time.time()
        system("bunzip2 --stdout %s > %s" % (tempSeqFile + ".bz2", tempSeqFile2))
        logger.critical("It took %s seconds to decompress the fasta file using system function" % (time.time() - startTime))
        logger.critical("File sizes, before: %s, compressed: %s, decompressed: %s" % (os.stat(tempSeqFile).st_size, os.stat(tempSeqFile + ".bz2").st_size, os.stat(tempSeqFile2).st_size))
        #Above test justifies out use of compression to reduce network transfer!
        #startTime = time.time()
        #runNaiveBlast([ tempSeqFile ], self.tempOutputFile, self.tempDir, lastzOptions="--nogapped --step=3 --hspthresh=3000 --ambiguous=iupac")
        #logger.critical("It took %s seconds to run blast" % (time.time() - startTime))
        

def compareResultsFile(results1, results2, closeness=0.95):
    results1 = loadResults(results1)
    logger.info("Loaded first results")
    
    #Now compare the results
    results2 = loadResults(results2)
    logger.info("Loaded second results")
    
    checkResultsAreApproximatelyEqual(ResultComparator(results2, results1), closeness)
    logger.info("Compared the blast results, using the first results as the 'true' results, and the second results as the predicted results")


def checkResultsAreApproximatelyEqual(resultsComparator, closeness=0.95):
    """Checks that the comparisons show the two blasts are suitably close together.
    """
    logger.critical("Results are: %s" % resultsComparator)
    assert resultsComparator.sensitivity >= closeness
    assert resultsComparator.specificity >= closeness
    
class ResultComparator:
    def __init__(self, trueResults, predictedResults):
        """Compares two sets of results and returns a set of statistics comparing them.
        """
        #Totals
        self.trueHits = trueResults[1]
        self.trueLength = len(trueResults[0])
        self.predictedHits = predictedResults[1]
        self.predictedLength = len(predictedResults[0])
        self.intersectionSize = len(trueResults[0].intersection(predictedResults[0]))
        #Sensitivity
        self.trueDifference = float(self.trueLength - self.intersectionSize)
        self.sensitivity = 1.0 - self.trueDifference / self.trueLength
        #Specificity
        self.predictedDifference = float(self.predictedLength - self.intersectionSize)
        self.specificity = 1.0 - self.predictedDifference / self.predictedLength
        #Union size
        self.unionSize = self.intersectionSize + self.trueDifference + self.predictedDifference
        #Symmetric difference
        self.symmDiff = self.intersectionSize / self.unionSize

    def __str__(self):
        return "True length: %s, predicted length: %s, union size: %s, \
intersection size: %s, symmetric difference: %s, \
true difference: %s, sensitivity: %s, \
predicted difference: %s, specificity: %s" % \
    (self.trueLength, self.predictedLength, self.unionSize, 
     self.intersectionSize, self.symmDiff,
     self.trueDifference, self.sensitivity,
     self.predictedDifference, self.specificity)

def loadResults(resultsFile):  
    """Puts the results in a set.
    """
    pairsSet = set()
    fileHandle = open(resultsFile, 'r')
    totalHits = 0
    for pairwiseAlignment in cigarRead(fileHandle):
        totalHits +=1
        i = pairwiseAlignment.start1
        s1 = 1
        if not pairwiseAlignment.strand1:
            i -= 1
            s1 = -1
            
        j = pairwiseAlignment.start2
        s2 = 1
        if not pairwiseAlignment.strand2:
            j -= 1
            s2 = -1
        
        for operation in pairwiseAlignment.operationList:
            if operation.type == PairwiseAlignment.PAIRWISE_INDEL_X:
                i += operation.length * s1
            elif operation.type == PairwiseAlignment.PAIRWISE_INDEL_Y:
                j += operation.length * s2
            else:
                assert operation.type == PairwiseAlignment.PAIRWISE_MATCH
                for k in xrange(operation.length):
                    if pairwiseAlignment.contig1 <= pairwiseAlignment.contig2:
                        if pairwiseAlignment.contig1 != pairwiseAlignment.contig2 or i != j: #Avoid self alignments
                            pairsSet.add((pairwiseAlignment.contig1, i, pairwiseAlignment.contig2, j)) 
                    else:
                        pairsSet.add((pairwiseAlignment.contig2, j, pairwiseAlignment.contig1, i))
                    i += s1
                    j += s2
        
        if pairwiseAlignment.strand1:
            assert i == pairwiseAlignment.end1
        else:
            assert i == pairwiseAlignment.end1-1
        
        if pairwiseAlignment.strand2:
            assert j == pairwiseAlignment.end2
        else:
            assert j == pairwiseAlignment.end2-1
            
        #assert j == pairwiseAlignment.end2
    fileHandle.close()      
    return (pairsSet, totalHits)

def runNaiveBlast(seqFile1, seqFile2, outputFile, 
                  blastString="cactus_lastz --format=cigar OPTIONS SEQ_FILE_1[multiple][nameparse=darkspace] SEQ_FILE_2[nameparse=darkspace] > CIGARS_FILE", 
                  lastzOptions=""):
    """Runs the blast command in a very naive way (not splitting things up).
    """
    open(outputFile, 'w').close() #Ensure is empty of results
    command = blastString.replace("OPTIONS", lastzOptions).replace("CIGARS_FILE", outputFile).replace("SEQ_FILE_1", seqFile1).replace("SEQ_FILE_2", seqFile2)
    startTime = time.time()
    system(command)
    return time.time()-startTime

def main():
    parseCactusSuiteTestOptions()
    sys.argv = sys.argv[:1]
    unittest.main()
        
if __name__ == '__main__':
    main()
