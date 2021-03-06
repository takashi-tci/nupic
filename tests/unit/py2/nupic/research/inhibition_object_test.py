#!/usr/bin/env python
# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2013, Numenta, Inc.  Unless you have purchased from
# Numenta, Inc. a separate commercial license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------

"""
Test if the firing number of coincidences after inhibition equals spatial pooler
numActivePerInhArea.

TODO: Fix this up to be more unit testy.
"""

import numpy

import unittest2 as unittest

from nupic.research import FDRCSpatial2

numpy.random.seed(100)



class InhibitionObjectTest(unittest.TestCase):

  def testInhibition(self):
    """
    Test if the firing number of coincidences after inhibition
    equals spatial poolernumActivePerInhArea.
    """
    # Miscellaneous variables:
    # n, w:                 n, w of encoders
    # inputLen:             Length of binary input
    # synPermConnected:     Spatial pooler synPermConnected
    # synPermActiveInc:     Spatial pooler synPermActiveInc
    # connectPct:           Initial connect percentage of permanences
    # coincidencesShape:    Number of spatial pooler coincidences
    # numActivePerInhArea:  Spatial pooler numActivePerInhArea
    # stimulusThreshold:    Spatial pooler stimulusThreshold
    # spSeed:               Spatial pooler for initial permanences
    # stimulusThresholdInh: Parameter for inhibition, default value 0.00001
    # kDutyCycleFactor:     kDutyCycleFactor for dutyCycleTieBreaker in
    #                       Inhibition
    # spVerbosity:          Verbosity to print other sp initial parameters
    # testIter:             Testing iterations
    n = 100
    w = 15
    inputLen = 300
    coincidencesShape = 2048
    numActivePerInhArea = 40
    stimulusThreshold = 0
    spSeed = 1956
    stimulusThresholdInh = 0.00001
    kDutyCycleFactor = 0.01
    spVerbosity = 0
    testIter = 100

    spTest = FDRCSpatial2.FDRCSpatial2(
                                coincidencesShape=(coincidencesShape, 1),
                                inputShape = (1, inputLen),
                                inputBorder = inputLen/2 - 1,
                                coincInputRadius = inputLen / 2,
                                numActivePerInhArea = numActivePerInhArea,
                                spVerbosity = spVerbosity,
                                stimulusThreshold = stimulusThreshold,
                                seed = spSeed
                                )
    initialPermanence = spTest._initialPermanence()
    spTest._masterPotentialM, spTest._masterPermanenceM = (
        spTest._makeMasterCoincidences(spTest.numCloneMasters,
                                       spTest._coincRFShape,
                                       spTest.coincInputPoolPct,
                                       initialPermanence,
                                       spTest.random))

    spTest._updateInhibitionObj()
    boostFactors = numpy.ones(coincidencesShape)

    for i in range(testIter):
      spTest._iterNum = i
      # random binary input
      input_ = numpy.zeros((1, inputLen))
      nonzero = numpy.random.random(inputLen)
      input_[0][numpy.where (nonzero < float(w)/float(n))] = 1

      # overlap step
      spTest._computeOverlapsFP(input_,
                                stimulusThreshold=spTest.stimulusThreshold)
      spTest._overlaps *= boostFactors
      onCellIndices = numpy.where(spTest._overlaps > 0)
      spTest._onCells.fill(0)
      spTest._onCells[onCellIndices] = 1
      denseOn = spTest._onCells

      # update _dutyCycleBeforeInh
      spTest.dutyCyclePeriod = min(i + 1, 1000)
      spTest._dutyCycleBeforeInh = (
          (spTest.dutyCyclePeriod - 1) *
          spTest._dutyCycleBeforeInh +denseOn) / spTest.dutyCyclePeriod
      dutyCycleTieBreaker = spTest._dutyCycleAfterInh.copy()
      dutyCycleTieBreaker *= kDutyCycleFactor

      # inhibition step
      numOn = spTest._inhibitionObj.compute(
          spTest._overlaps + dutyCycleTieBreaker, spTest._onCellIndices,
          stimulusThresholdInh,  # stimulusThresholdInh
          max(spTest._overlaps)/1000,  # addToWinners
      )
      # update _dutyCycleAfterInh
      spTest._onCells.fill(0)
      onCellIndices = spTest._onCellIndices[0:numOn]
      spTest._onCells[onCellIndices] = 1
      denseOn = spTest._onCells
      spTest._dutyCycleAfterInh = (((spTest.dutyCyclePeriod-1) *
                                    spTest._dutyCycleAfterInh + denseOn) /
                                   spTest.dutyCyclePeriod)

      # learning step
      spTest._adaptSynapses(onCellIndices, [], input_)

      # update boostFactor
      spTest._updateBoostFactors()
      boostFactors = spTest._firingBoostFactors

      # update dutyCycle and boost
      if ((spTest._iterNum+1) % 50) == 0:
        spTest._updateInhibitionObj()
        spTest._updateMinDutyCycles(
            spTest._dutyCycleBeforeInh,
            spTest.minPctDutyCycleBeforeInh,
            spTest._minDutyCycleBeforeInh)
        spTest._updateMinDutyCycles(
            spTest._dutyCycleAfterInh,
            spTest.minPctDutyCycleAfterInh,
            spTest._minDutyCycleAfterInh)

      # test numOn and spTest.numActivePerInhArea
      self.assertEqual(numOn, spTest.numActivePerInhArea,
                       "Error at input %s, actual numOn are: %i, "
                       "numActivePerInhAre is: %s" % (
                           i, numOn, numActivePerInhArea))



if __name__=="__main__":
  unittest.main()
