import unittest

import os, sys
from sonLib.bioio import cigarReadFromString, cigarWrite
from sonLib.bioio import popenCatch
from sonLib.bioio import logger
from sonLib.bioio import TestStatus
from sonLib.bioio import getTempFile
from sonLib.bioio import getTempDirectory
from sonLib.bioio import system

from cactus.shared.common import runLastz
from cactus.shared.common import runSelfLastz
from cactus.shared.common import runCactusRealign
from cactus.shared.common import runCactusSelfRealign
from cactus.shared.common import runCactusCoverage

class TestCase(unittest.TestCase):
    
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.tempDir = getTempDirectory(os.getcwd())
        self.tempFiles = []
        unittest.TestCase.setUp(self)
        self.tempOutputFile = os.path.join(self.tempDir, "results1.txt")
        self.tempFiles.append(self.tempOutputFile)
        self.tempOutputFile2 = os.path.join(self.tempDir, "results2.txt")
        self.tempFiles.append(self.tempOutputFile2) 
        self.encodePath = os.path.join(TestStatus.getPathToDataSets(), "MAY-2005")
        self.defaultLastzArguments = "--ambiguous=iupac"
        self.defaultRealignArguments = ""

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        
    def testCactusRealignDummy(self):
        """Runs cactus realign using the "rescoreOriginalAlignment" mode
        and checks the output is equivalent to what you'd get by just running lastz.
        """
        for seqFile1, seqFile2 in seqFilePairGenerator():

            lastzOutput = getTempFile(rootDir=self.tempDir)
            runLastz(seqFile1, seqFile2, alignmentsFile=lastzOutput,
                     lastzArguments=self.defaultLastzArguments,
                     work_dir=self.tempDir)
            realignOutput = getTempFile(rootDir=self.tempDir)
            runCactusRealign(seqFile1, seqFile2, inputAlignmentsFile = lastzOutput,
                             outputAlignmentsFile = realignOutput,
                             realignArguments=self.defaultRealignArguments + " --rescoreOriginalAlignment",
                             work_dir=self.tempDir)
                                      
            for realignLine, lastzLine in zip([ i for i in open(lastzOutput, 'r') if i != '' ],
                                              [ i for i in open(realignOutput, 'r') if i != '' ]):
                realignCigar = cigarReadFromString(realignLine)
                lastzCigar = cigarReadFromString(lastzLine)
                self.assertTrue(realignCigar != None)
                self.assertTrue(realignCigar == lastzCigar)
    
    def testCactusRealign(self):
        """Runs cactus realign using the default parameters and checks that the realigned output cigars align
        the same subsequences.
        """
        for seqFile1, seqFile2 in seqFilePairGenerator():
            lastzOutput = getTempFile(rootDir=self.tempDir)
            runLastz(seqFile1, seqFile2, alignmentsFile=lastzOutput,
                     lastzArguments=self.defaultLastzArguments,
                     work_dir=self.tempDir)
            realignOutput = getTempFile(rootDir=self.tempDir)
            runCactusRealign(seqFile1, seqFile2, inputAlignmentsFile = lastzOutput,
                             outputAlignmentsFile = realignOutput,
                             realignArguments=self.defaultRealignArguments,
                             work_dir=self.tempDir)
            
            for realignLine, lastzLine in zip([ i for i in open(lastzOutput, 'r') if i != '' ], 
                                              [ i for i in open(realignOutput, 'r') if i != '' ]):
                realignCigar = cigarReadFromString(realignLine)
                lastzCigar = cigarReadFromString(lastzLine)
                self.assertTrue(realignCigar.sameCoordinates(lastzCigar))
    
    def testCactusRealignSplitSequences(self):
        """Runs cactus realign, splitting indels longer than 100bp, and check
        that the coverage from the results is the same as the coverage from
        realigning with no arguments.."""
        for seqFile1, seqFile2 in seqFilePairGenerator():
            lastzOutput = getTempFile(rootDir=self.tempDir)
            runLastz(seqFile1, seqFile2, alignmentsFile=lastzOutput,
                     lastzArguments=self.defaultLastzArguments,
                     work_dir=self.tempDir)
            
            realignOutput = getTempFile(rootDir=self.tempDir)
            runCactusRealign(seqFile1, seqFile2, inputAlignmentsFile=lastzOutput,
                             outputAlignmentsFile=realignOutput,
                             realignArguments=self.defaultRealignArguments,
                             work_dir=self.tempDir)
            
            splitRealignOutput = getTempFile(rootDir=self.tempDir)
            runCactusRealign(seqFile1, seqFile2, inputAlignmentsFile=lastzOutput,
                             outputAlignmentsFile=splitRealignOutput,
                             realignArguments=self.defaultRealignArguments + " --splitIndelsLongerThanThis 100",
                             work_dir=self.tempDir)

            # Check coverage on seqFile1
            splitRealignCoverage = runCactusCoverage(seqFile1, splitRealignOutput, work_dir=self.tempDir)
            realignCoverage = runCactusCoverage(seqFile1, realignOutput, work_dir=self.tempDir)
            self.assertTrue(splitRealignCoverage == realignCoverage)
            # Check coverage on seqFile2
            splitRealignCoverage = runCactusCoverage(seqFile2, splitRealignOutput, work_dir=self.tempDir)
            realignCoverage = runCactusCoverage(seqFile2, realignOutput, work_dir=self.tempDir)
            self.assertTrue(splitRealignCoverage == realignCoverage)
            os.remove(realignOutput)
            os.remove(splitRealignOutput)

    def testCactusRealignRescoreByIdentityAndProb(self):
        """Runs cactus realign using the default parameters and checks that the realigned output cigars align 
        the same subsequences.
        """
        for seqFile1, seqFile2 in seqFilePairGenerator():
            lastzOutput = getTempFile(rootDir=self.tempDir)
            runLastz(seqFile1, seqFile2, alignmentsFile=lastzOutput,
                     lastzArguments=self.defaultLastzArguments,
                     work_dir=self.tempDir)

            realignByIdentityOutput = getTempFile(rootDir=self.tempDir)
            runCactusRealign(seqFile1, seqFile2, inputAlignmentsFile=lastzOutput,
                             outputAlignmentsFile=realignByIdentityOutput,
                             realignArguments=self.defaultRealignArguments + " --rescoreByIdentity",
                             work_dir=self.tempDir)

            realignByPosteriorProbOutput = getTempFile(rootDir=self.tempDir)
            runCactusRealign(seqFile1, seqFile2, inputAlignmentsFile=lastzOutput,
                             outputAlignmentsFile=realignByPosteriorProbOutput,
                             realignArguments=self.defaultRealignArguments + " --rescoreByPosteriorProb",
                             work_dir=self.tempDir)

            realignByIdentityIgnoringGapsOutput = getTempFile(rootDir=self.tempDir)
            runCactusRealign(seqFile1, seqFile2, inputAlignmentsFile=lastzOutput,
                             outputAlignmentsFile=realignByIdentityIgnoringGapsOutput,
                             realignArguments=self.defaultRealignArguments + " --rescoreByIdentityIgnoringGaps",
                             work_dir=self.tempDir)
            for realignLineByIdentity, realignLineByPosteriorProb, realignLineByIdentityIgnoringGaps, lastzLine in \
                                          zip([ i for i in open(realignByIdentityOutput, 'r') if i != '' ], \
                                              [ i for i in open(realignByPosteriorProbOutput, 'r') if i != '' ], \
                                              [ i for i in open(realignByIdentityIgnoringGapsOutput, 'r') if i != '' ], \
                                              [ i for i in open(lastzOutput, 'r') if i != '' ]):
                realignCigarByIdentity = cigarReadFromString(realignLineByIdentity)
                realignCigarByPosteriorProb = cigarReadFromString(realignLineByPosteriorProb)
                realignCigarByIdentityIgnoringGaps = cigarReadFromString(realignLineByIdentityIgnoringGaps)
                lastzCigar = cigarReadFromString(lastzLine)
                #Check scores are as expected
                self.assertTrue(realignCigarByIdentity.score >= 0)
                self.assertTrue(realignCigarByIdentity.score <= 100.0)
                self.assertTrue(realignCigarByPosteriorProb.score >= 0)
                self.assertTrue(realignCigarByPosteriorProb.score <= 100.0)
                self.assertTrue(realignCigarByIdentityIgnoringGaps.score >= 0)
                self.assertTrue(realignCigarByIdentityIgnoringGaps.score <= 100.0)
                #print "Scores", "Rescore by identity", realignCigarByIdentity.score, "Rescore by posterior prob", realignCigarByPosteriorProb.score, "Rescore by identity ignoring gaps", realignCigarByIdentityIgnoringGaps.score, "Lastz score", lastzCigar.score

                            
def seqFilePairGenerator():
    if "SON_TRACE_DATASETS" not in os.environ:
        return
     ##Get sequences
    encodePath = os.path.join(TestStatus.getPathToDataSets(), "MAY-2005")
    encodeRegions = [ "ENm00" + str(i) for i in xrange(1,2) ] #, 2) ] #Could go to six
    species = ("human", "mouse") #, "dog")#, "chimp") 
    #Other species to try "rat", "monodelphis", "macaque", "chimp"
    for encodeRegion in encodeRegions:
        regionPath = os.path.join(encodePath, encodeRegion)
        for i in xrange(len(species)):
            species1 = species[i]
            for species2 in species[i+1:]:
                seqFile1 = os.path.join(regionPath, "%s.%s.fa" % (species1, encodeRegion))
                seqFile2 = os.path.join(regionPath, "%s.%s.fa" % (species2, encodeRegion))
                yield seqFile1, seqFile2
        
if __name__ == '__main__':
    unittest.main()
