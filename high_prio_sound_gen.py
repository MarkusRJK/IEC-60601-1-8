#!/usr/bin/python 

from __future__ import division
from wavtools import getVolumes
from wavtools import volumesOutOfDbRange
from wavtools import hasEnoughHarmonics
from wavtools import hasSignificantVolumesInsideDbRange
from wavtools import getMax
from wavtools import save_wav
from wavtools import IEC_60601_1_8_Pulse
from wavtools import PulseMerger
from wavtools import introduction
from wavtools import maxDiffSoundPressureToPulseFrequencyInDB
from shutil   import copyfile
import subprocess
import os
import sys

# specify, where you want to save the file and its filename:
#outputFilePath = os.environ['HOME'] + "/Downloads/sounds/high-prio-new.wav"
outputFilePath = "new-hp.wav"
# name where a new configuration is saved:
# IMPORTANT NOTE: name must be the same as in the (next) import statement
#                 below around line 116
hpConfigFilename = 'hp_alarm'
# if you want to also remote copy it to a device via scp, specify
# the remote target here in the form of a scp target, e.g.
# someuser@host:path. See scp for more details. If you set
# the remote to None, no attempt for scp is made.
remoteSCPtarget = None


# NOTE: you will see several sections of settings the later overwriting the
#       priors. This is intented so you can see the history where it began.


###############################################################################
# Default Settings
###############################################################################
# See IEC_60601_1_8_*_Pulse class for spacing, duration, rise and fall ranges
#
# NOTE: there were scripts to generate 8kHz and 44.1kHz bursts
defaultSampleRate_Hz = 44100
# NOTE: pulse spacing in initial script did not cover from 90% of the fall
#       mark to 90% of the rise mark
defaultPulseSpacing_ms = 95
# NOTE: pulse duration in initial script did not cover from 90% of the rise
#       mark to 90% of the fall mark
defaultPulseDuration_ms = 150
defaultRiseTime_pc = 15
defaultFallTime_pc = 15
defaultBaseFrequency1 = 400
defaultBaseFrequency2 = 400
#
defaultHarmonicStr1 = "1 3 5 7 9"
defaultHarmonicStr2 = "1 3 5 7 9"
defaultVolumeStr1 = "1.0  0.85 0.6 0.5  0.4"
defaultVolumeStr2 = "1.0  0.85 0.6 0.5  0.4"
# spacing between pulses 5 and 6 (out of 10 pulses)
defaultHalfBurstSpacing_ms = 1000
# spacing between two bursts
defaultBurstSpacing_ms = 2459.53
# NOTE: the intial script output 5 wave files that had to be merged with an
#       external tool e.g. audacity. Audacity caused clippings whatever way
#       it merged the files.
# gain in (0.0; 1.0]
gain = 0.98

###############################################################################
# Some devices may require a small silence period at the start of a HP alarm
# default should be 0
###############################################################################

defaultStartWithSilence_ms = 0

###############################################################################
###############################################################################
###############################################################################

if len(sys.argv) > 1:
    copyfile(sys.argv[1], 'hp_alarm.py')
# NOTE: This import must come after all initialization.
#       By the way Python is made hp_alarm must be located in the directory in
#       which THIS script (high_prio_sound_gen.py) resides.
try:
    from hp_alarm import defaultSampleRate_Hz
    from hp_alarm import defaultPulseSpacing_ms
    from hp_alarm import defaultPulseDuration_ms
    from hp_alarm import defaultRiseTime_pc
    from hp_alarm import defaultFallTime_pc
    from hp_alarm import defaultBaseFrequency1
    from hp_alarm import defaultHarmonicStr1
    from hp_alarm import defaultVolumeStr1
    from hp_alarm import defaultBaseFrequency2
    from hp_alarm import defaultHarmonicStr2
    from hp_alarm import defaultVolumeStr2
    from hp_alarm import defaultHalfBurstSpacing_ms
    from hp_alarm import defaultBurstSpacing_ms
    from hp_alarm import defaultStartWithSilence_ms
except:
    print("No config " + hpConfigFilename + ".py found\n")
    pass

# TODO:
# the follwing comment is left in here, if someone wants to create another script
# for medium priority alarms
# medium priority alarm pulse duration (t_d): 125ms to 250ms
#pulseDurationMP_ms_min=125
#pulseDurationMP_ms_max=250

def HP_introduction():
    print "Terminology - High Priority Alarm:"
    print "                                                              burst"
    print "                                                              spacing"
    print "                                                             |-->"
    print "|------------------------- burst -----------------------------|"
    print "| |pulse|pulse|pulse|            | half  |                   ||"
    print "| | ___ |space| ___ |       ___  | burst |  ___         ___  ||"
    print "| |/   \       /   \|      /   \ | space | /   \       /   \ ||"
    print "| /     \     /     \     /     \|       |/     \     /     \||"
    print "|/freq. 1\___/freq. 1\___/freq. 1\_______/freq. 2\___/freq. 2\|____"
    print ""
    print "Please set the maximum sound pressure difference to the fundamental"
    print "frequency of (at least 4) harmonics in wavtools.py."

   
# pulses may have different tones within this range:
baseFrequency_Hz_min = 150
baseFrequency_Hz_max = 1000

class IEC_60601_1_8_High_Priority_Pulse(IEC_60601_1_8_Pulse):
    """
    Inherits from IEC_60601_1_8_Pulse and sets pulseDuration_ms_min|max
    and pulse_90pc_spacing_ms_min|max for High Priority alarms.
    """
    
    # high priority pulses spacing t_s (measured from 90% of the fall to 90% of the rise)
    pulse_90pc_spacing_ms_min=50
    pulse_90pc_spacing_ms_max=125
    _pulse_90pc_spacing_ms = None

    # high priority alarm pulse duration (t_d): 125ms to 250ms
    pulseDuration_ms_min=75
    pulseDuration_ms_max=200
    
    halfBurstSpacing_ms_min=350
    halfBurstSpacing_ms_max=1300
    
    burstSpacing_ms_min=2500 
    burstSpacing_ms_max=15000
    
    def setHalfBurstSpacing_ms(self, hbs = None):
        """
        a burst consists of 5 pulses and another 5 pulses where we call 
        the silcence between these two 5 pulses halfBurstSpacing_ms.
        It is in milliseconds (measured from 90% mark of the rise
        to 90% mark of the fall)
        """
        if hbs is None:
            self._halfBurstSpacing_ms = (self._halfBurstSpacing_ms_min + self._halfBurstSpacing_ms_max) / 2.0
        else:
            self._halfBurstSpacing_ms = max(0, hbs)
        return self._halfBurstSpacing_ms

    def getHalfBurstSpacing_ms(self):
        return self._halfBurstSpacing_ms

    def isHalfBurstSpacingInRange(self):
        return self._halfBurstSpacing_ms >= self.halfBurstSpacing_ms_min and self._halfBurstSpacing_ms <= self.halfBurstSpacing_ms_max

    def setBurstSpacing_ms(self, bs = None):
        """
        spacing between two bursts in milliseconds (measured from 90% mark of the rise
        to 90% mark of the fall)
        """
        if bs is None:
            self._burstSpacing_ms = (self.burstSpacing_ms_min + self.burstSpacing_ms_max) / 2.0
        else:
            self._burstSpacing_ms = max(0, bs)
        return self._burstSpacing_ms

    def getBurstSpacing_ms(self):
        return self._burstSpacing_ms

    def isBurstSpacingInRange(self):
        return self._burstSpacing_ms >= self.burstSpacing_ms_min and self._burstSpacing_ms <= self.burstSpacing_ms_max


###############################################################################
###############################################################################
###############################################################################

print
introduction()
print
HP_introduction()
print
print

sampleRate_Hz = defaultSampleRate_Hz
try:
    select = input("Sample rate\n  0) 8kHz\n  1) 9.6kHz\n  2) 12kHz\n  3) 16kHz\n  4) 19.2kHz\n  5) 24kHz\n  6) 32kHz\n  7) 44.1kHz\n  8) 48kHz\n  9) 96kHz\nSelect [0; 9] (default: " + str(defaultSampleRate_Hz) + "): ")
    if select == 0:
        sampleRate_Hz = 8000
    if select == 1:
        sampleRate_Hz = 9600
    if select == 2:
        sampleRate_Hz = 12000
    if select == 3:
        sampleRate_Hz = 16000
    if select == 4:
        sampleRate_Hz = 19200
    if select == 5:
        sampleRate_Hz = 24000
    if select == 6:
        sampleRate_Hz = 32000
    if select == 7:
        sampleRate_Hz = 44100
    if select == 8:
        sampleRate_Hz = 48000
    if select == 9:
        sampleRate_Hz = 96000
except:
    pass
        
print("==> Selected sample rate: " + str(sampleRate_Hz) + " Hz\n")

pulse = IEC_60601_1_8_High_Priority_Pulse()
pulse.setSampleRate_Hz(sampleRate_Hz)

###############################################################################

try:
    pulseSpacing_ms = input("Pulse spacing [" + str(pulse.pulse_90pc_spacing_ms_min) +  "ms; " + str(pulse.pulse_90pc_spacing_ms_max) + "ms] (default: " + str(defaultPulseSpacing_ms) + "ms): ")
except:
    pulseSpacing_ms = defaultPulseSpacing_ms

print("==> Selected pulse spacing: " + str(pulse.setPulseSpacing_ms(pulseSpacing_ms)) + " ms")
if (not pulse.isPulseSpacingInRange()):
    print("*** WARNING: pulse spacing out of range")
print

###############################################################################

try:
    pulseDuration_ms = input("Pulse duration [" + str(pulse.pulseDuration_ms_min) +  "ms; " + str(pulse.pulseDuration_ms_max) + "ms] (default: " + str(defaultPulseDuration_ms) + "ms): ")
except:
    pulseDuration_ms = defaultPulseDuration_ms

print("==> Selected pulse duration: " + str(pulse.setPulseDuration_ms(pulseDuration_ms)) + " ms")
if (not pulse.isPulseDurationInRange()):
    print("*** WARNING: pulse duration out of range")
print
 
###############################################################################

try:
    riseTime_pc = input("Rise time [" + str(pulse.riseTime_pc_min) +  "%; " + str(pulse.riseTime_pc_max) + "%] (default: " + str(defaultRiseTime_pc) + "%): ")
except:
    riseTime_pc = defaultRiseTime_pc  # 100 * (11 / 125) = 8.8% measures with Audaciy

print("==> Selected rise time: " + str(pulse.setRiseTime_pc(riseTime_pc)) + " %")
if (not pulse.isRiseTimeInRange()):
    print("*** WARNING: rise time out of range")
print

###############################################################################

try:
    fallTime_pc = input("Fall time [0%; 100%] (default: " + str(defaultFallTime_pc) + "%): ")
except:
    fallTime_pc = defaultFallTime_pc

print("==> Selected fall time: " + str(pulse.setFallTime_pc(fallTime_pc)) + " %")
if (not pulse.isFallTimeInRange()):
    print("*** WARNING: fall time out of range")
print

###############################################################################

try:
    baseFrequency1 = input("Base frequency of 1st pulse [" + str(baseFrequency_Hz_min) + "Hz; " + str(baseFrequency_Hz_max) + "Hz] (default: " + str(defaultBaseFrequency1) + "Hz): ")
except:
    baseFrequency1 = defaultBaseFrequency1 
  
print("==> Selected base frequency of 1st pulse: " + str(baseFrequency1))
# IEC 60601-1-8 page 17 requires base frequency in range [150Hz, 1000Hz]
if (baseFrequency_Hz_min > baseFrequency1 or baseFrequency1 > baseFrequency_Hz_max):
    print("*** WARNING: pulse frequency f_0 out of range")
print

# to keep this code simple we leave this task to the user: first harmonic is 1 and harmonics
# are sorted ascending.
print("IMPORTANT NOTE: the first harmonic must be 1 and the harmonics must be in ascending order!!!")
harmonicsStr1 = raw_input("Harmonics [positive integer] (default: " + defaultHarmonicStr1 + "): ")
if len(harmonicsStr1) == 0:
    harmonicsStr1 = defaultHarmonicStr1
 
print("==> Selected harmonics of 1st pulse: " + harmonicsStr1)
   
harmonics1 = harmonicsStr1.split()
noHarmonics = len(harmonics1)

# hasEnoughHarmonics ensures the correct format of harmonics. Hence call before
# working on harmonics
if (not hasEnoughHarmonics(baseFrequency1, harmonics1)):
    print("*** WARNING: less than required number of harmonics in range [300Hz, 4000Hz]")
print

###############################################################################

volumes1 = []
while len(volumes1) != noHarmonics:
    volumesStr1 = raw_input(str(noHarmonics) + " Volumes (default: " + defaultVolumeStr1 + "): ")
    if len(volumesStr1) == 0:
        volumesStr1 = defaultVolumeStr1
    volumes1 = getVolumes(volumesStr1)

print("==> Selected volumes of 1st pulse: " + volumesStr1)

dBvalue=str(maxDiffSoundPressureToPulseFrequencyInDB)
if (not hasSignificantVolumesInsideDbRange(volumes1, baseFrequency1, harmonics1)):
    print("*** WARNING: less than 4 harmonics with volumes +-" + dBvalue + "dB from base frequency's volume")
    print("            "),
    vOODbR = volumesOutOfDbRange(volumes1)
    print("             The following volumes differ more than " + dBvalue + "dB from base frequency's volume:")
    for v in vOODbR:
        print(str(v) + ", "),
print

###############################################################################

try:
    baseFrequency2 = input("Base frequency of 2nd pulse [" + str(baseFrequency_Hz_min) + "Hz; " + str(baseFrequency_Hz_max) + "Hz] (default: " + str(defaultBaseFrequency2) + "Hz): ")
except:
    baseFrequency2 = defaultBaseFrequency2
 
print("==> Selected base frequency of 2nd pulse: " + str(baseFrequency2))
# IEC 60601-1-8 page 17 requires base frequency in range [150Hz, 1000Hz]
if (baseFrequency_Hz_min > baseFrequency2 or baseFrequency2 > baseFrequency_Hz_max):
    print("*** WARNING: pulse frequency f_0 out of range [150Hz, 1000Hz]")
print

# to keep this code simple we leave this task to the user: first harmonic is 1 and harmonics
# are sorted ascending.
print("IMPORTANT NOTE: the first harmonic must be 1 and the harmonics must be in ascending order!!!")
harmonicsStr2 = raw_input("Harmonics [positive integer] (default: " + defaultHarmonicStr2 + "): ")
if len(harmonicsStr2) == 0:
    harmonicsStr2 = defaultHarmonicStr2
 
print("==> Selected harmonics of 2nd pulse: " + harmonicsStr2)
   
harmonics2 = harmonicsStr2.split()
noHarmonics = len(harmonics2)

# hasEnoughHarmonics ensures the correct format of harmonics. Hence call before
# working on harmonics
if (not hasEnoughHarmonics(baseFrequency2, harmonics2)):
    print("*** WARNING: less than required number of harmonics in range [300Hz, 4000Hz]")
print

###############################################################################

volumes2 = []
while len(volumes2) != noHarmonics:
    volumesStr2 = raw_input(str(noHarmonics) + " Volumes (default: " + defaultVolumeStr2 + "): ")
    if len(volumesStr2) == 0:
        volumesStr2 = defaultVolumeStr2
    volumes2 = getVolumes(volumesStr2)

print("==> Selected volumes of 2nd pulse: " + volumesStr2)

dBvalue=str(maxDiffSoundPressureToPulseFrequencyInDB)
if (not hasSignificantVolumesInsideDbRange(volumes2, baseFrequency2, harmonics2)):
    print("*** WARNING: less than 4 harmonics with volumes +-" + dBvalue + "dB from base frequency's volume")
    print("            "),
    vOODbR = volumesOutOfDbRange(volumes2)
    print("             The following volumes differ more than " + dBvalue + "dB from base frequency's volume:")
    for v in vOODbR:
        print(str(v) + ", "),
print

###############################################################################

try:
    halfBurstSpacing_ms = input("Spacing between first 5 pulses and second 5 pulses in ms [" + str(pulse.halfBurstSpacing_ms_min) +  "ms; " + str(pulse.halfBurstSpacing_ms_max) + "ms] (default: " + str(defaultHalfBurstSpacing_ms) + "ms): ")
except:
    halfBurstSpacing_ms = defaultHalfBurstSpacing_ms

print("==> Selected half burst spacing: " + str(pulse.setHalfBurstSpacing_ms(halfBurstSpacing_ms)) + " ms")
if (not pulse.isHalfBurstSpacingInRange()):
    print("*** WARNING: half burst spacing out of range")
print

###############################################################################

try:
    burstSpacing_ms = input("Spacing between two bursts in ms [" + str(pulse.burstSpacing_ms_min) +  "ms; " + str(pulse.burstSpacing_ms_max) + "ms] (default: " + str(defaultBurstSpacing_ms) + "ms): ")
except:
    burstSpacing_ms = defaultBurstSpacing_ms

print("==> Selected burst spacing: " + str(pulse.setBurstSpacing_ms(burstSpacing_ms)) + " ms")
if (not pulse.isBurstSpacingInRange()):
    print("*** WARNING: burst spacing out of range")
print

###############################################################################

try:
    print("Some devices require a silence period at the very start")
    print("which is beyond IEC 60601-1-8 compliance.")
    startWithSilence_ms = input("Silence at start in ms (default: " + str(defaultStartWithSilence_ms) + "ms): ")
except:
    startWithSilence_ms = defaultStartWithSilence_ms

startWithSilence_ms = max(0, startWithSilence_ms)
print("==> Selected silence at start: " + str(startWithSilence_ms) + " ms")
print

###############################################################################

doSave = 'y'
try:
    doSave = raw_input("Save parameters as new defaults [Y|n]? ")
except:
    doSave = 'y'

if (doSave != 'n' and doSave != 'N'):
    try:
        f=open(hpConfigFilename + ".py","w")
        f.write("#!/usr/bin/python"                                          + "\n" +
                "defaultSampleRate_Hz       = "   + str(sampleRate_Hz)       + "\n" +
                "defaultPulseSpacing_ms     = "   + str(pulseSpacing_ms)     + "\n" +
                "defaultPulseDuration_ms    = "   + str(pulseDuration_ms)    + "\n" +
                "defaultRiseTime_pc         = "   + str(riseTime_pc)         + "\n" +
                "defaultFallTime_pc         = "   + str(fallTime_pc)         + "\n" +
                "defaultBaseFrequency1      = "   + str(baseFrequency1)      + "\n" +
                "defaultHarmonicStr1        = \"" + str(harmonicsStr1)       + "\"\n" +
                "defaultVolumeStr1          = \"" + str(volumesStr1)         + "\"\n" +
                "defaultBaseFrequency2      = "   + str(baseFrequency2)      + "\n" +
                "defaultHarmonicStr2        = \"" + str(harmonicsStr2)       + "\"\n" +
                "defaultVolumeStr2          = \"" + str(volumesStr2)         + "\"\n" +
                "defaultHalfBurstSpacing_ms = "   + str(halfBurstSpacing_ms) + "\n" +
                "defaultBurstSpacing_ms     = "   + str(burstSpacing_ms)     + "\n" +
                "defaultStartWithSilence_ms = "   + str(startWithSilence_ms) + "\n")
        f.close()
        print("Configuration saved in " + hpConfigFilename + ".py\n")
    except:
        print(hpConfigFilename + ".py locked by other application - please close\n")
        raw_input()

###############################################################################

print "\n#############################################\n"
print "\nDetermine max volume across all pulses"
maxVol1 = getMax(volumes1)
maxVol2 = getMax(volumes2)
maxVol  = max(maxVol1, maxVol2)    

if maxVol == 0:
    raise ValueError('volumes of all harmonics in pulses cannot be all 0')

###############################################################################

# create array of integer volumes and normalize volume across all volChar1+2
print "Normalizing volumes across pulses"

# it is maxVol != 0
for i, vol in enumerate(volumes1):
    volumes1[i] = vol / maxVol
for i, vol in enumerate(volumes2):
    volumes2[i] = vol / maxVol

###############################################################################

# pulse1/2 are arrays of harmonics
pulse1 = []
pulse2 = []

print "Creating wave and harmonics for pulse 1"
for i, volume in enumerate(volumes1):
    pulse1.append(pulse.createWave(baseFrequency1 * int(harmonics1[i]), volume))
print "Creating wave and harmonics for pulse 2"
for i, volume in enumerate(volumes2):
    pulse2.append(pulse.createWave(baseFrequency2 * int(harmonics2[i]), volume))

###############################################################################

print "Merging harmonics and creating final burst with 10 pulses"
# merge the audio files
audio = []

p1 = PulseMerger(pulse1)
p1Array = p1.merge()
print "Pulse 1:\t" + str(pulse.getPulseDuration_ms()) + "ms"
audio = audio + p1Array
maxAbs1 = p1.getMaxVolume()

# IEC 60601-1-8 page 17 - silence btw Pulse 1 and 2: x = 50ms to 125ms
# x is here called pulse_90pc_spacing_ms (see also wavetools.py)
print "Silence 1:\t" + str(pulse.getPulseSpacing_ms()) + "ms"
audio = audio + pulse.createSilence()
   
print "Pulse 2:\t" + str(pulse.getPulseDuration_ms()) + "ms"
audio = audio + p1Array

# IEC 60601-1-8 page 17 - silence btw Pulse 2 and 3: x = 50ms to 125ms
print "Silence 2:\t" + str(pulse.getPulseSpacing_ms()) + "ms"
audio = audio + pulse.createSilence()

print "Pulse 3:\t" + str(pulse.getPulseDuration_ms()) + "ms"
audio = audio + p1Array

# IEC 60601-1-8 page 17 - silence btw Pulse 3 and 4: 2 x + t_d, x 
# t_d is here called pulseDuration_ms (see also wavetools.py)
silenceBtw3_and_4 = 2 * pulse.getPulseSpacing_ms() + pulse.getPulseDuration_ms() + 10
print "Silence 3:\t" + str(silenceBtw3_and_4) + "ms"
audio = audio + pulse.createSilence(silenceBtw3_and_4)

p2 = PulseMerger(pulse2)
p2Array = p2.merge()
print "Pulse 4:\t" + str(pulse.getPulseDuration_ms()) + "ms"
audio = audio + p2Array
maxAbs2 = p2.getMaxVolume()

maxAbs = max(maxAbs1, maxAbs2)
# maxAbs != 0 since maxVol != 0

# IEC 60601-1-8 page 17 - silence btw Pulse 4 and 5: x = 50ms to 125ms
print "Silence 4:\t" + str(pulse.getPulseSpacing_ms()) + "ms"
audio = audio + pulse.createSilence()

print "Pulse 5:\t" + str(pulse.getPulseDuration_ms()) + "ms"
audio = audio + p2Array

# IEC 60601-1-8 page 17 - silence btw Pulse 5 and 6: 0.35 to 1.3 seconds
# here called halfBurstSpacing_ms
print "Silence 5:\t" + str(pulse.getHalfBurstSpacing_ms()) + "ms"
# see IEC 60601-1-8 page 17
print "Pulse 6-10:\trepeat pulse 1-5" # add total length of 1-5 incl. spacing
audio = ([0.0] * pulse._getSamplesFromMs(startWithSilence_ms)) + audio + pulse.createSilence(pulse.getHalfBurstSpacing_ms()) + audio

# IEC 60601-1-8 page 17 - silence btw two bursts: 2.5 to 15.0 seconds
# here called burstSpacing_ms
print "Silence 10:\t" + str(pulse.getBurstSpacing_ms()) + "ms"
# NOTE: since we copied pulse 1-5 for pulses 6-10 we also copied the
#       halfBurstSpace after pulse 5 which we now need to subtract
#       from the burstSpacing
audio = audio + pulse.createSilence(pulse.getBurstSpacing_ms())

###############################################################################

# checking IEC 60601-1-8 Table 3:
maxDiffSoundPressureAnyPulsesInDB=10
maxDiffSoundPressureAnyPulses=10.0**(maxDiffSoundPressureAnyPulsesInDB/20.0)
# Max difference in amplitude between any two PULSES is 10dB (as factor: 3.16)
if maxAbs2 != 0 and maxAbs1 / maxAbs2 > maxDiffSoundPressureAnyPulses:
    print("*** WARNING: more than " + maxDiffSoundPressureAnyPulses + "dB difference in amplitude between pulses\n")
if maxAbs1 != 0 and maxAbs2 / maxAbs1 > maxDiffSoundPressureAnyPulses:
    print("*** WARNING: more than " + maxDiffSoundPressureAnyPulses + "dB difference in amplitude between pulses\n")

###############################################################################

print "Setting max gain across burst to " + str(gain)
  
# set the volume of the final output here:
if maxAbs != 0:
    scale = gain / maxAbs
else:
    scale = 0

for i, sample in enumerate(audio):
    audio[i] = sample * scale

###############################################################################

print "Saving wave in " + outputFilePath

save_wav(audio, outputFilePath, sampleRate_Hz)

###############################################################################

if remoteSCPtarget != None:
    print "Copying " + outputFilePath + " to " + remoteSCPtarget
    subprocess.check_output(['scp', outputFilePath, remoteSCPtarget])

print("All Done!")
