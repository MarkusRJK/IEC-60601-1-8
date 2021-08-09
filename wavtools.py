# -*- coding: utf-8 -*-
"""
Created on Mon Nov  4 13:00:11 2019

@author: markus
"""
import math
import wave
import struct

debug = True

# Maximum difference of sound pressure to fundamental frequency of
# harmonic components in the 300Hz - 4000Hz band (at least 4 of
# these harmonic components must be within the frequency band and
# sound pressure limitation).
# See: table 4 in IEC 60601-1-8:2007
maxDiffSoundPressureToPulseFrequencyInDB=15

def introduction():
    print "Terminology:"
    print
    print "                          |<--- pulse spacing ---|"
    print "          t_3          t_4.                      ."
    print "100%......|_pulse durat._|.                      . _______"
    print "90%....../...............\.                      ./"
    print "        /.               .\                      /"
    print "       / .               . \                    /"
    print "      /  .               .  \                  /"
    print "10%../ . . . . . . . . . . . \                /"
    print " ___/.   t_2           t_5   .\_________0____/"
    print "     t_1                     t_6"
    print "     |< >|               |< >|"
    print "     rise                fall time"
    print 
    print "t_1:  10% mark of risetime"
    print "t_2:  90% mark of risetime"
    print "t_3: 100% mark of risetime"
    print "t_4: start of fall"
    print "t_5:  90% mark of falltime"
    print "t_6:  10% mark of falltime"

# some usefull utilities:
def getVolumes(s):
    """ 
    Converts a string with floats (e.g. '0.1 3.1 5.77')
    to an array of floats (e.g. [0.1 3.1 5.77]).
    Limits all array elements to (0.0; 1.0].
    """
    volStrArray = s.split()
    volumes = []
    for vol in volStrArray:
        try:
            fVol = float(vol)
            if (fVol <= 0.0):
                # volume 0 is not allowed (and does not make sense)
                print "negative volume " + vol + " replaced by absolute"
                volumes.append(-fVol)
            elif (fVol > 1.0):
                print "volume > 1.0: " + vol + " - replaced by 1.0"
                volumes.append(1.0)
            else:
                volumes.append(fVol)
        except:
            print vol + " is not a float - replacing by 0.0"
            volumes.append(0.0)
    return volumes

def volumesOutOfDbRange(volumes):
    """
    Collect and returns all the volumes that differ more than
    'maxDiffSoundPressureToPulseFrequencyInDB'
    (by standard: 15dB) from the base frequency's volume
    (volumes[0]).
    Pre-condition: all volumes > 0 
                   and the first harmonic (base frequency 
                   and base volume) is the first array entry
    """
    vOutOfRange = []
    baseVolume = None
    maxSoundPressureDiff=10.0**(maxDiffSoundPressureToPulseFrequencyInDB/20.0)

    for v in volumes:
        if baseVolume == None:
            baseVolume = v
        else:
            if v > maxSoundPressureDiff * baseVolume:
                vOutOfRange.append(v)
            if maxSoundPressureDiff * v < baseVolume:
                vOutOfRange.append(v)
    return vOutOfRange

def getMax(array):
    """
    Maximum of an array of floats or ints with positive values
    """
    maximum = 0
    for v in array:
        maximum = max(v, maximum)
    return maximum

# \param harmonics is an array of strings with integers, e.g. "1 3 4 5"
def hasEnoughHarmonics(baseFrequency, harmonics):
    """
    harmonics is an array of integers where each integer is 
    represented as a string!!, e.g. "1" "3" "4" "5"
    NOTE: the standard says that at least 4 harmonics must 
          be present for better spacial location of the sound
          it does not mention that those 4 harmonics must be
          in the range [300Hz; 4000Hz]. 
          The latter range ensures that older people can hear
          all frequencies. 
          It makes sense to force the 4 harmonics into this
          range.
    """
    inRangeHarmonicCtr = 0
    for h in harmonics: # h is a string element (split!)
        try:
            hFrequency = int(h) * baseFrequency
        except:
            raise TypeError('Harmonics contained non-integer values')
        if 300 <= hFrequency and hFrequency <= 4000:
            inRangeHarmonicCtr += 1
    return inRangeHarmonicCtr >= 4

def hasSignificantVolumesInsideDbRange(volumes, baseFrequency, harmonics):
    """
    Counts the volumes of harmonics with frequencies inside the [300Hz; 4000Hz]
    range that are in the '+-maxDiffSoundPressureToPulseFrequencyInDB' 
    (by standard: 15dB) range of the baseFrequency.
    Pre-condition: all volumes > 0 and length of harmonics == length of volumes
                   and the first harmonic is 1 (= baseFrequency)
    """
    maxSoundPressureDiff=10.0**(maxDiffSoundPressureToPulseFrequencyInDB/20.0)
    counter = 0
    baseVolume = None
    for index, v in enumerate(volumes):
        if baseVolume == None:
            baseVolume = v
        else: # 10^(15/20) = 5.62
            hFrequency = int(harmonics[index]) * baseFrequency
            if 300 <= hFrequency and hFrequency <= 4000:
                # this is a significant harmonic
                if v <= maxSoundPressureDiff * baseVolume and maxSoundPressureDiff * v >= baseVolume:
                    counter = counter + 1

    # baseFrequency with baseVolume is the reference and within bands by definition
    # i.e. counter 3 means 4 volumes in range
    return (counter >= 3)

###############################################################################

class Pulse:
    """
    One pulse in the burst. A pulse is defined by:
    - the rise time to
    - the pulse duration
    - the fall time
    - the sample rate and 
    - the maxAbsAmplitude
    The pulse can be decorated with a volume and frequency when
    the wave is created.
    """
    _pulseDuration_ms = None
    _riseTime_pc = None
    _fallTime_pc = None
    
    # NOTE: 32767 = 0xFFFF / 2
    def __init__(self, pulseDuration_ms = None, riseTime_pc = None, fallTime_pc = None, sampleRate_Hz = 8000, maxAbsAmplitude = 32767):
        """sample_rate and bit_depth must be same across the audio file"""
        self.setSampleRate_Hz(sampleRate_Hz)
        self.setMaxAbsAmplitude(maxAbsAmplitude)
        if pulseDuration_ms != None:
            self.setPulseDuration_ms(pulseDuration_ms)
        if riseTime_pc != None:
            self.setRiseTime_pc(riseTime_pc)
        if fallTime_pc != None: 
            self.setFallTime_pc(fallTime_pc)

    def setSampleRate_Hz(self, sampleRate_Hz):
        if sampleRate_Hz == 0:
            raise ValueError('sampleRate_Hz must not be 0')
        self._sampleRate_Hz = sampleRate_Hz
        
    def setMaxAbsAmplitude (self, maxAbsAmplitude):
        self._maxAbsAmplitude = maxAbsAmplitude
        
    def _getSamplesFromMs(self, ms):
        """milliseconds to sample counts"""
        return int(ms * 0.001 * self._sampleRate_Hz)
    
    def setPulseDuration_ms(self, pulseDuration_ms):
        """
        calculates the number of samples for the given pulse duration
        in milliseconds
        """
        self._pulseDuration_ms = pulseDuration_ms
        
    def _getPulseDuration_samples(self):
        if self._pulseDuration_ms is None:
            raise ValueError('pulse duration was not set')
        return self._getSamplesFromMs(self._pulseDuration_ms)

    def setRiseTime_pc(self, riseTime_pc):
        """
        the rise time is given in percentage of the pulse duration,
        i.e. a value btw. 0 and 100
        """
        if riseTime_pc == 0.0:
            raise ValueError('rise time must not be 0')
        self._riseTime_pc = riseTime_pc
        
    def _getRiseTime_samples(self):
        if self._riseTime_pc is None:
            raise ValueError('rise time in percent was not set')
        return int(self._riseTime_pc/100.0 * self._getPulseDuration_samples())
        
    def setFallTime_pc(self, fallTime_pc):
        """
        the fall time is given in percentage of the pulse duration,
        i.e. a value btw. 0 and 100
        """
        if fallTime_pc == 0.0:
            raise ValueError('fall time must not be 0')
        self._fallTime_pc = fallTime_pc
        
    def _getFallTime_samples(self):
        if self._fallTime_pc is None:
            raise ValueError('rise time in percent was not set')
        return int(self._fallTime_pc/100.0 * self._getPulseDuration_samples())
        
    def createSilence(self, duration_ms = None):
        """Creates a IEC60601-1-8 compliant silence between two pulses,
        i.e. the requested duration of the silence is shortened by 
        the rise and fall time part that is considered silence, too.
        See Terminology 'pulse spacing'.
        Returns a 'silence array'"""
        if duration_ms == 0.0:
            return []
        if duration_ms is None:
            # take 90% samples of the rise and of the fall as space is measured
            # from the 90% mark in the fall to the 90% mark in the rise
            numberOfSamples = self._getPulseSpacing_samples() - int((self._getRiseTime_samples() + self._getFallTime_samples()) * 0.9)
        else:
            numberOfSamples = self._getSamplesFromMs(duration_ms) - int((self._getRiseTime_samples() + self._getFallTime_samples()) * 0.9)
        silenceArray = [0.0] * numberOfSamples
        return silenceArray

    def _createAmplitudeProfile(self):
        ampArray = []
    
        # Timing Model:
        #                           |<-------- t_s --------|
        #           t_3          t_4.                      .  
        # 100%......|_____t_d______|.  a(t): amplification . ________
        # 90%....../...............\.        at time t     ./
        #         /.               .\                      /
        #   ar(t)/ .               . \af(t)               /
        #       /  .               .  \                  /
        # 10%../ . . . . . . . . . . . \                /
        #     /.   t_2           t_5   .\_________0____/
        #  t_0 t_1                   t_6 t_7
        #
        # Note: if this "graphics" is displayed in italic (phyton comment)
        #       you may copy it to an editor without decorations since the
        #       slopes do not look good with italic.
        #
        # t_0: start of the signal (ar(t_0) = 0); t_0 := 0
        # t_1: raised to 10% of full amplitude (ar(t_1) = 0.1)
        # t_2: raised to 90% of full amplitude (ar(t_2) = 0.9)
        # t_3: reached full amplitude (vr(t_3) = 1)
        # t_4: start of fall (af(t_4) = 1)
        # t_5: amplitude fell to 90% (af(t_5) = 0.9)
        # t_6: amplitude fell to 10% (af(t_6) = 0.1)
        # t_7: end of the signal (vf(t_7) = 0)
        #
        #         / 0       for t < t_0
        #        /  ar(t)   for t_0 <= t < t_3
        # a(t) =    1       for t_3 <= t < t_4
        #        \  af(t)   for t_4 <= t < t_7
        #         \ 0       for t >= t_7
        #
        # timing relations: 
        # t_r = t_2 - t_1
        # t_d = t_5 - t_2 = self._getPulseDuration_samples()
        # t_f = t_6 - t_5
        # t_5 - t_4 = self._getPulseDuration_samples() * (1 - fallTime_perc/100.0) / 2.0
        #
        # functions: 
        # ar(t) = r * t                raising slope
        # af(t) = 1 + f * (t - t_4)    falling slope
        #
        # conclusions:
        #
        # ar(t_2) - ar(t_1) = 0.8 = r * (t_2 - t_1) =   r * t_r
        # vf(t_5) - vf(t_6) = 0.8 = f * (t_5 - t_6) = - f * t_f
        
        # first generate the amplitude profile with timebase 1/sample_rate
        # i.e. 1 sample is the time unit
        
        # slopes: _getRise|FallTime_samples() != 0
        rSlope =  0.8 / self._getRiseTime_samples()
        fSlope = -0.8 / self._getFallTime_samples()    
    
        # counters:
        pulseDuration_sample = self._getPulseDuration_samples()
    
        # create rising slope
        sample = 0
        while True:
            # get the amplitude of the sample
            amplification = rSlope * sample
            sample += 1
            if (amplification > 1.0):     # 100% amplification reached or t_3
                # no amplification beyond 1.0 gets into ampArray
                break
            if (amplification >= 0.9):    # 90% amplification reached or t_2
                pulseDuration_sample -= 1 # count down pulse duration
            ampArray.append(amplification)
    
        # create flat amplitude
        # fallTime_samples is the number of samples to fall from 90% to 10%
        # i.e. fall by 80%. To fall by 10% (from 100% to 90%)
        # we have 1/8th of fallTime_samples
        startFall = self._getFallTime_samples()/8.0
        # number of samples with full amplitude:
        numberOfSamples = int(pulseDuration_sample - startFall + 1)
        constAmplitudeArray = [1.0] * numberOfSamples
        ampArray = ampArray + constAmplitudeArray # concatenate both arrays

        # create falling slope
        sample = 0
        while True:
            # get the amplitude of the sample
            amplification = fSlope * sample + 1.0
            sample += 1
            if (amplification < 0.0):
                break
            ampArray.append(amplification)

        # assert all volumes in ampArray are in the range [0.0; 1.0]
        if debug and not all(v <= 1.0 for v in ampArray):
            raise ValueError('One or more volumes in ampArray exceed 1.0 (100%) in rising slope')
        if debug and not all(v >= 0.0 for v in ampArray):
            raise ValueError('One or more volumes in ampArray are negative in rising slope')
        return ampArray
  
    def createWave(self, frequency_Hz, volume):
        """
        Returns an array of samples with amplitudes in [-volume, volume]
        volume is expected to be btw. 0 and 1.0
        """
        amplitudeProfile = self._createAmplitudeProfile()
        volume = min(max(volume, 0.0), 1.0)
        pulse = []
        i = 0
        for sample in amplitudeProfile:
            # multiply i with 1.0 to make float (in case __future__ is not there)
            value = sample * volume * math.sin(2.0 * math.pi * frequency_Hz * ( (1.0 * i) / self._sampleRate_Hz ))
            pulse.append(value)
            
            # assert all values in range [0.0; 1.0]
            if debug and (abs(value) > 1.0):
                raise ValueError('Wave sample out of range [0.0; 1.0]')
            i += 1
        return pulse

# \details Inherits from Pulse and adds setters and range checkers
#          as specified by IEC_60601_1_8. Setting a out of range value
#          is allowed however a warning will be printed.
#          Defaults are taken as medium between min and max.
class IEC_60601_1_8_Pulse(Pulse):

    # pulses spacing t_s (measured from 90% of the fall to 90% of the rise)
    pulse_90pc_spacing_ms_min=125
    pulse_90pc_spacing_ms_max=250
    _pulse_90pc_spacing_ms = None

    # alarm pulse duration (t_d): depends on priority of alarm
    pulseDuration_ms_min=0
    pulseDuration_ms_max=0
    _pulseDuration_ms = None

    # NOTE: the previous versions of this script contained 10%-40% which
    #       was a type!!!
    # rise time of alarm pulse (t_r): 10% - 20% of pulseDuration
    riseTime_pc_min=10
    riseTime_pc_max=20
    _riseTime_pc = None
    _fallTime_pc = None

    def setPulseDuration_ms(self, pulseDuration_ms = None):
        """
        Pulses duration t_d in milliseconds (measured from 90% mark of the rise
        to 90% mark of the fall)
        """
        if pulseDuration_ms is None:
            self._pulseDuration_ms = (self.pulseDuration_ms_min + self.pulseDuration_ms_max) / 2.0
        else:
            self._pulseDuration_ms = max(0, pulseDuration_ms)
        return self._pulseDuration_ms
        
    def getPulseDuration_ms(self):
        return self._pulseDuration_ms

    def isPulseDurationInRange(self):
        return self._pulseDuration_ms >= self.pulseDuration_ms_min and self._pulseDuration_ms <= self.pulseDuration_ms_max
    
    def setPulseSpacing_ms(self, pulseSpacing_ms = None):
        """
        Pulses duration t_s in milliseconds (measured from 90% mark of the fall
        to 90% mark of the rise)
        """
        if pulseSpacing_ms is None:
            self._pulse_90pc_spacing_ms = (self.pulse_90pc_spacing_ms_min + self.pulse_90pc_spacing_ms_max) / 2.0
        else:
            self._pulse_90pc_spacing_ms = max(0, pulseSpacing_ms)
        return self._pulse_90pc_spacing_ms
        
    def getPulseSpacing_ms(self):
        return self._pulse_90pc_spacing_ms

    def isPulseSpacingInRange(self):
        return self._pulse_90pc_spacing_ms >= self.pulse_90pc_spacing_ms_min and self._pulse_90pc_spacing_ms <= self.pulse_90pc_spacing_ms_max

    def _getPulseSpacing_samples(self):
        if self._pulse_90pc_spacing_ms is None:
            raise ValueError('pulse duration was not set')
        return self._getSamplesFromMs(self._pulse_90pc_spacing_ms)

    def setRiseTime_pc(self, riseTime_pc = None):
        """
        The rise time is given in percentage of the pulse duration,
        i.e. a value btw. 0 and 100
        """
        if riseTime_pc is None:
            self._riseTime_pc = (self.riseTime_pc_min + self.riseTime_pc_max) / 2.0
        else:
            self._riseTime_pc = min(max(0, riseTime_pc), 100)
        return self._riseTime_pc
        
    def isRiseTimeInRange(self):
        return self._riseTime_pc >= self.riseTime_pc_min and self._riseTime_pc <= self.riseTime_pc_max

    def setFallTime_pc(self, fallTime_pc = None):
        """
        The fall time is given in percentage of the pulse duration,
        i.e. a value btw. 0 and 100
        """
        if fallTime_pc is None:
            self._fallTime_pc = self._riseTime_pc
        else:
            self._fallTime_pc = min(max(0, fallTime_pc), 100)
        return self._fallTime_pc
         
    def isFallTimeInRange(self):
        pulseSpacing_samples = self._getPulseSpacing_samples()
        fallTime_samples     = self._getFallTime_samples()         
        riseTime_samples     = self._getRiseTime_samples()
        return riseTime_samples + fallTime_samples <= pulseSpacing_samples


###############################################################################

class PulseMerger:
    """
    Merges pulses which must have the same number of samples
    """
    def __init__(self, pulses):
        self._pulses = pulses
        self._maxHarmonic = len(pulses) - 1
        for i in range(self._maxHarmonic):
            if (len(pulses[self._maxHarmonic]) != len(pulses[i])):
                raise ValueError('Equal number of samples in all pulses required')

    def merge(self):
        """
        Pulses is an array of pulses with different harmonics
        """
        audio = []
        self._maxAbs = 0
        for i, sample1 in enumerate(self._pulses[self._maxHarmonic]):
            sample = sample1
            for harmonic in range(self._maxHarmonic):
                sample += self._pulses[harmonic][i]
            if (abs(sample) > self._maxAbs):
                self._maxAbs = abs(sample)
            audio.append(sample)
        return audio

    def getMaxVolume(self):
        return self._maxAbs
        
        
    

def save_wav(audio, file_name, sample_rate, bit_depth=32767):
    # Open up a wav file
    repeat = True
    while repeat:
        try:
            wav_file=wave.open(file_name,"w")
            repeat = False
        except:
            print(file_name + " locked by other application - please close\n")
            raw_input()
    # wav params
    nchannels = 1

    sampwidth = 2

    # 44100 is the industry standard sample rate - CD quality.  If you need to
    # save on file size you can adjust it downwards. The stanard for low quality
    # is 8000 or 8kHz.
    nframes = len(audio)
    comptype = "NONE"
    compname = "not compressed"
    wav_file.setparams((nchannels, sampwidth, sample_rate, nframes, comptype, compname))

    # WAV files here are using short, 16 bit, signed integers for the 
    # sample size.  So we multiply the floating point data we have by 32767, the
    # maximum value for a short integer.  NOTE: It is theortically possible to
    # use the floating point -1.0 to 1.0 data directly in a WAV file but not
    # obvious how to do that using the wave module in python.
    for sample in audio:
        wav_file.writeframes(struct.pack('h', int( sample * bit_depth )))

    wav_file.close()

    return
    
