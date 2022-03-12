#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AR Closed-Caption System
@author: Ben Brown <benbr0wn@uw.edu>
"""

import argparse
import cv2
import datetime
import speech_recognition

# Speech
latestRecognizedPhrase = ""
timeOfRecognition = None
maxDisplayTimeS = 2 # Max number of seconds to display recognized text

# adjust_for_ambient_noise auto sets this
#micEnergyThresholdPct = 0.5 # Range of 50 - 4000, but log scale

# Webcam/Video
idealRes = (1280, 720)
idealFps = 24

def recognizerCallback(recognizer, audio):
    global latestRecognizedPhrase, timeOfRecognition
    try:
        #latestRecognizedPhrase = recognizer.recognize_sphinx(audio)
        latestRecognizedPhrase = recognizer.recognize_azure(audio, location="westus", key="f76c2b2d0ac64659b4a5a18abc236753")
        timeOfRecognition = datetime.datetime.now()
    except speech_recognition.UnknownValueError:
        # Sphinx could not understand audio
        latestRecognizedPhrase = ""
    except speech_recognition.RequestError as e:
        print("Sphinx error; {0}".format(e))
        latestRecognizedPhrase = "[recognition error]"
        return

def addRecognizedTextToImage(imageFrame, speakerPosition=None):
    '''
        Writes over imageFrame with contents of lastRecognizedPhrase
    '''

    global latestRecognizedPhrase, timeOfRecognition

    if len(latestRecognizedPhrase) == 0:
        return

    font = cv2.FONT_HERSHEY_SIMPLEX
    text = latestRecognizedPhrase
    fontScale = 1.25
    fontThickness = 2

    textFgColor = (255,255,255)
    textBgColor = (0,0,0)

    renderedTextSize, baseline = cv2.getTextSize(text, font, fontScale, fontThickness)
    borderMargin = int(baseline)

    height, width, channels = imageFrame.shape

    # Place text in bottom middle or provided position
    textOrigin = (0,0) # TL
    if speakerPosition is not None:
        textOrigin = speakerPosition
    else:
        bottomOffset = 50
        textOrigin = (
            int(width / 2.0 - renderedTextSize[0] / 2.0), 
            height - renderedTextSize[1] - bottomOffset)

    bgTL = (textOrigin[0] - borderMargin, textOrigin[1] - borderMargin - renderedTextSize[1])
    bgBR = (
        bgTL[0] + renderedTextSize[0] + borderMargin * 2,
        bgTL[1] + renderedTextSize[1] + borderMargin * 2)

    cv2.rectangle(imageFrame, bgTL, bgBR, textBgColor, -1)
    cv2.putText(
        imageFrame, 
        latestRecognizedPhrase, 
        textOrigin,
        font,
        fontScale,
        textFgColor,
        fontThickness,
        cv2.LINE_AA)

    # Clear text display if it has been onscreen too long
    timeOfDisplay = datetime.datetime.now()
    if timeOfRecognition is not None:
        delta = timeOfDisplay - timeOfRecognition
        if delta.seconds > maxDisplayTimeS:
            latestRecognizedPhrase = ""
    
def startVideoLoop(videoPath=None, camDeviceId=0, micDeviceId=0):
    video = None
    audio = None
    stopMic = None

    print("Starting Speech Recognizer")
    speechRec = speech_recognition.Recognizer()
    #speechRec.energy_threshold = ((4000 - 50)*micEnergyThresholdPct)+50

    audioVideoPlayer = None

    usingWebcam = videoPath is None
    
    if not usingWebcam:
        from ffpyplayer.player import MediaPlayer
        # ffpyplayer? https://stackoverflow.com/questions/46864915/python-add-audio-to-video-opencv
        print("Starting video parser: "+str(videoPath))
        video = cv2.VideoCapture(videoPath)
        audioVideoPlayer = MediaPlayer(videoPath)
    else:
        print("Starting PyAudio/PocketSphinx")
        try:
            import pyaudio
            import pocketsphinx
            print("PyAudio/PocketSphinx loaded")
        except:
            print("PyAudio could not be loaded")
            return
        
        mic = speech_recognition.Microphone(micDeviceId)
        with mic as source:
            print("Now collecting ambient noise... "+str(source))
            speechRec.adjust_for_ambient_noise(source, duration=5)

        stopMic = speechRec.listen_in_background(mic, recognizerCallback, phrase_time_limit=1.0)
        
        print("Starting webcam input from device "+str(camDeviceId))
        video = cv2.VideoCapture(camDeviceId)
    if video is None or not video.isOpened():
        print("Video parser was not started")
        return

    if usingWebcam:
        video.set(cv2.CAP_PROP_FPS, idealFps)
        video.set(cv2.CAP_PROP_FRAME_WIDTH, idealRes[0])
        video.set(cv2.CAP_PROP_FRAME_HEIGHT, idealRes[1])

    fps = video.get(cv2.CAP_PROP_FPS)
    msecPerFrame = int(1000.0 / fps)

    vidW = video.get(cv2.CAP_PROP_FRAME_WIDTH)
    vidH = video.get(cv2.CAP_PROP_FRAME_HEIGHT)

    print("Starting capture loop at %dx%d and %.1f fps. Press q to quit any time." % 
        (vidW, vidH, fps))
    while True:
        if not usingWebcam:
            _, val = audioVideoPlayer.get_frame(show=False)
            if val == 'eof':
                break
        ret, frame = video.read()
        if ret is not True:
            break
        addRecognizedTextToImage(frame)
        cv2.imshow('Frame', frame)
        if cv2.waitKey(msecPerFrame) & 0xFF == ord('q'):
            break

    if stopMic is not None:
        stopMic(wait_for_stop=False)
        print("Mic capture released")

    if not usingWebcam:
        audioVideoPlayer.close_player()

    video.release()
    print("Video capture released")
    cv2.destroyAllWindows()


def init(args):
    if args.enumMics:
        print("Detected microphone source:")
        # Enumerate microphone devices
        for deviceId, name in enumerate(speech_recognition.Microphone.list_microphone_names()):
            print(str(deviceId)+": "+name)
        return
    useVideo = ('videoPath' in args and 
        args.videoPath is not None and 
        len(args.videoPath) > 0)
    if useVideo:
        print('Init using video')
        startVideoLoop(args.videoPath)
    else:
        startVideoLoop(None, args.camIdx, args.micIdx)
        
    print("End")
    
argParser = argparse.ArgumentParser(description='AR Real-Time Closed Caption System')
argParser.add_argument(
    '--videoPath', 
    type=str, 
    help='process video file instead of live webcam input')
argParser.add_argument(
    '--enumMics',
    action='store_true',
    help='this switch will print out located microphone device IDs')
argParser.add_argument(
    '--micIdx',
    type=int,
    default=0,
    help='microphone device ID')
argParser.add_argument(
    '--camIdx',
    type=int,
    default=0,
    help='camera device ID')
    
init(argParser.parse_args())