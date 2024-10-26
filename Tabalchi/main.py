#(C) Shreyan Mitra

#Imports
import json #For parsing .tabla files
from jsonschema import validate #For checking .tabla files for validity
from __future__ import annotations
from abc import ABC, abstractmethod #For defining abstract classes
from playsound import playsound #For playing sounds
from pydub.playback import play as pydubplay #Also for playing sounds
from pydub import AudioSegment #For merging and joining sounds
import audio_effects as ae # For slowing down sounds
import acoustid #For fingerprinting audio files
import chromaprint #For decoding audio fingerprints
from typing import* #For type hints
from types import SimpleNamespace #For accessing dictionary field using dot notation
import os #For moving files
from pathlib import Path #Also for moving files
import warnings #For warnings
from transformers import pipeline # For composition generation
import torch #For model inference
import random #For generating random speed if only speed class is provided
from collections import OrderedDict #For representing an ordered mapping of phrases to actual number of syllables taken for each phrase
import fsspec #For downloading recordings folder from Github

#A class representing an interval of beats
class BeatRange():
    '''
    Class representing a beat range

    Parameters:
        begin(int): The start beat of the beat range, inclusive
        end(int): The end beat of the beat range, exclusive
    '''
    def __init__(self, begin:int, end:int):
        assert begin < end, "BeatRange end beat must be greater than begin beat"
        self.begin = begin
        self.end = end

    @classmethod
    def fromString(self, spec:str) -> Self: #In the format num1-num2 (no spaces allowed)
            numbers = spec.split("-")
            num1 = int(numbers[0])
            num2 = int(numbers[1])
            return BeatRange(num1, num2)

    def range(self) -> int:
        '''
        Returns the number of beats represented by this beat range
        '''
        return self.end - self.begin

    @classmethod
    def isContiguousSequence(cls, ranges:List[Self], totalBeats:int) -> bool:
        '''
        Returns if a particular beat range convers all beats from 1 to the given total number of beats

        Parameters:
            ranges(List[BeatRange]): A list of beat ranges
            totalBeats(int): The total number of beats in the sequence to check the ranges against
        '''
        ranges = sorted(ranges, lambda range: range.begin)
        for i in range(1, len(ranges)):
            if ranges[i].begin != ranges[i-1].end:
                return False
        if(ranges[-1].end < totalBeats or ranges[0].begin != 1):
            return False
        return True

    @classmethod
    def getSubsequence(cls, ranges:List[Self], begin:int, end:int) -> List[Self]:
        '''
        Returns the ranges, in sorted order, that fall between a given begin and end beat

        Parameters:
            ranges(List[BeatRange]): A list of beat ranges to choose from
            begin(int): The start beat of the desired sequence
            end(int): The end beat of the desired sequence
        '''
        subsequence = []
        for i in range(len(ranges)):
            range = ranges[i]
            if range.begin >= begin and range.end <= end:
                subsequence.append(range)
            elif range.begin >= begin and range.end > end:
                subsequence.append(BeatRange(range.begin, end))
            elif range.begin < begin and range.end <= end:
                subsequence.append(BeatRange(begin, range.end))
            else:
                subsequence.append(BeatRange(begin, end))
        return sorted(subsequence)

#A class representing a composition type. Ex. Kayda, Rela, etc.
#For descriptions of the different types of tabla compositions, visit www.tablalegacy.com (not affiliated with this product or the author in any way)
#Sometimes, differences between types of compositions are hard to quantify, and come down to the "feel" of the composition.
class CompositionType():
    registeredTypes = {} # A class variable keeping track of the list of registered composition types
    '''
    A class to represent a composition type

    Parameters:
        name(str): The name of the composition type. Ex. Kayda, Rela, etc.
        schema(dict): The structure of the components field of the .tabla file
        validityCheck(Callable[[Bol],[bool]]): A function that returns whether a given Bol is of the composition type being considered
        assembler(Callable[[SimpleNamespace], [list[str]]]): Gives instructions on how to put together the disjointed components of the composition
        register(bool): Whether to register the composition type (i.e. to save it for future use). By default, True
    '''
    def __init__(self, name:str, schema:dict, validityCheck:Callable[[Bol],[bool]], assembler:Callable[[SimpleNamespace], [list[str]]], register:bool = True):
        self.name = name
        self.schema = schema
        self.assembler = assembler
        def preValidityCheck(bol:dict) -> bool:
            try:
                validate(instance = bol, schema = schema)
                return True
            except Exception as e:
                print(e)
                return False

        self.preCheck = preValidityCheck #This is used within the BolParser before BolParser turns the .tabla file into a Bol (Note to parser: only pass in components field here)
        self.mainCheck = validityCheck #This is used within the BolParser with a fully instantiated Bol object
        if register:
            CompositionType.registeredTypes.update({name: self})

#A class representing something with an associated number. Ex. Taal, Jati, Speed, etc.
class Numeric(ABC):
    '''
    A class representing something that has an associated number
    '''
    @property
    @abstractmethod
    def name(self):
        ...

    @property
    @abstractmethod
    def number(self):
        ...

#A class representing a Taal
class Taal(Numeric):
    registeredTaals = {}
    '''
    A class representing a taal. Ex. Teental, Rupaak, etc.
    '''
    def __init__(self, beats:int, taali:list[int] = [], khali:list[int] = [], name:Union[str, None] = None, theka:Union[str, None] = None, register:bool = True):
        self.beats = beats
        self.taali = taali
        self.khali = khali
        if not name:
            self.id = str(beats)
        else:
            self.id = name
        self._theka = theka
        if register:
            Taal.registeredTaals.update({self.id: self})

    @property
    def name(self):
        return self.id
    @property
    def number(self):
        return self.beats
    @property
    def theka(self):
        return self._theka
    @theka.setter
    def theka(self, theka):
        self._theka = theka

#A class representing a jati
class Jati(Numeric):
    registeredJatis = {}
    '''
    A class representing a Jati
    '''
    def __init__(self, syllables:int, name:Union[str, None] = None, register = True):
        self.syllables = syllables
        if not name:
            self.id = str(syllables)
        else:
            self.id = name
        if register:
            Jati.registeredJatis.update({self.id: self})

    @property
    def name(self):
        return self.id
    @property
    def number(self):
        return self.syllables

#A class that represents a speed category
class SpeedClasses:
    registeredSpeeds = {}
    '''
    A class representing a Speed class
    '''
    def __init__(self, inClassCheck: Callable[[int], [bool]], randomGenerate:Callable[[],[int]], name:str, register:bool = True):
        self.check = inClassCheck
        self.generator = randomGenerate
        self.id = name
        if register:
            SpeedClasses.registeredSpeeds.update({name: self})

    @classmethod
    def getSpeedClassFromBPM(cls, bpm:int) -> str:
        for key, value in SpeedClasses.registeredSpeeds.items():
            if value.check(bpm):
                return key

#A class that represents a specific speed
class Speed(Numeric):
    '''
    Class that represents a particular speed. Ex. 62bpm
    '''
    def __init__(self, specifier:Union[int, str]):
        if isinstance(specifier, str):
            self.speedClass = specifier
            self.bpm = SpeedClasses.registeredSpeeds[specifier].generator()
        else:
            self.bpm = specifier
            self.speedClass = SpeedClasses.getSpeedClassFromBPM(specifier)

    @property
    def name(self):
        return self.speedClass
    @property
    def number(self):
        return self.bpm



class Notation(ABC):

    VALID_NOTATIONS = ["Bhatkande", "Paluskar"] #No registered here because there can only be two types of notation

    @classmethod
    @abstractmethod
    def toString(self, bol:Bol):
        ...

    @classmethod
    def display(cls, bol:Bol, fileName:str):
        print(Notation.toString(bol), file = fileName)

#TODO
class Bhatkande(Notation):
    pass

#TODO
class Paluskar(Notation):
    pass

class Bol():
    '''
    A class representing a bol, a collection of beats
    '''
    def __init__(self, beats:list[Beat], notationClass:Union[Type[Notation], None] = None):
        self.beats = beats
        self.notationClass = notationClass
        self.markedBeats = []
        self.markedPhrases = []
        for beat in beats:
            lst = beat.phrases
            for i in range(len(lst)):
                if(beat.markers[i] == 1):
                    self.markedBeats.append(beat)
                    self.markedPhrases.append(lst[i][0])

    def play(self):
        for beat in self.beats:
            beat.play()

    def write(self, filename:str, notationClass:Union[Type[Notation], None]):
        if notationClass is not None:
            notationClass.display(self, filename)
        elif self.notationClass is not None:
            self.notationClass.display(self, filename)
        else:
            raise ValueError("No Notation object found to use.")

class Beat():
    '''
    A class representing a collection of phrases
    '''
    def __init__(self, number:int, taaliKhaliOrNone:Literal[-1,0,1], saam:bool, phrases:list[tuple], speed:int, markers:list[Literal[0,1]]):
        self.number = number
        assert len(markers) == len(phrases), "Invalid length for marker array. At beat number " + str(number) + ". \nMarkers: " + str(markers) + "\nPhrases: " + str(phrases)
        self.markers = markers
        self.clap = taaliKhaliOrNone
        self.saam = saam
        self.speed = speed
        duration = 60.0/speed #In seconds (this is the duration of the entire beat)
        jati = 0
        for item in phrases:
            jati += item[1]
        syllableDuration = duration/jati #This is duration of a specific segment of the beat
        self.multipliers = []
        self.soundFiles = []
        for item in phrases:
            phrase = item[0]
            syllables = item[1]
            self.multipliers.append(((syllables*1.0)/phrase.syllables) * (syllableDuration/0.25)) #Since, in the original recording, one syllable = 0.25 seconds
            self.soundFiles.append(phrase.soundBite.recording)
        self.phrases = phrases

    def play(self):
        for index in range(len(self.soundFiles)):
            s = AudioSegment.from_file(self.soundFiles[index])
            if self.multipliers[index] >= 1:
                s = s.speedup(self.multipliers[index])
            else:
                s = ae.speed_down(s, self.multipliers[index])
            pydubplay(s)





class Fetcher:
    #Class that contains several static methods involving fetching sounds and variables
    @classmethod
    def fetch(cls, id, specifier = None, componentIDs = None) -> Sound:
        '''
        Fetch the Sound object given a phrase identifier, or synthesize it from componentIDs given a specifier

        Parameters:
            id(string): The identifier for the sound
            specifier(string or None): If the sound does not exist and needs to be specified, whether the phrase is a composite or sequential phrase
            componentIDs(list[string] or None): A list of the identifiers making up a composite or sequential phrases

        Returns:
            newSound (Sound) OR oldSound (Sound): The Sound instance representing the given id

        Throws:
            ValueError: if invalid specifier is passed for sound synthesis
        '''
        oldSound = Sound.sounds.get(id)
        if oldSound: #If a Sound object with the given identifier exists
            return oldSound #return the sound object
        elif not specifier: #We did not find the Sound object and no specifier was provided for synthesizing the new sound
            raise ValueError("Did not find soundbite " + str(id) + ". Have you preregistered the id? Otherwise, you should just pass the soundBite when initializing the phrase. Debug Info: " + str(oldSound))
        #For both of the following cases, componentIDs must also be specified
        elif specifier == "composite": #A composite sound consists of two sounds played at the same time. Ex. dha = ge + na
            assert componentIDs, "Need to specify component ids for composite phrases."
            newSound = Sound(id, Sound.merge(Sound.sounds.get(c) for c in componentIDs)) #Create a new sound by using the Sound class' static merge function
            return newSound #The new sound will be stored in Sound.sounds, but we return it anyway for convenience
        elif specifier == "sequential": #A sequential sound consists of a sequence of sounds played in succession Ex. terekite = te, re, ki, te
            assert componentIDs, "Need to specify component ids for sequential phrases."
            newSound = Sound(id, Sound.join(Sound.sounds.get(c) for c in componentIDs)) #Create a new sound by using the Sound class' static join function
            return newSound #The new sound will be stored in Sound.sounds, but we return it anyway for convenience
        else: #At this point, the specifier was not one of ["composite", "sequential"] and we do not know what to do
            raise ValueError("Invalid specifier passed.")


    @classmethod
    def addRecording(cls, file):
        '''
        A method to add an audio file recording to the recordings folder.
            file(str): Path to MIDI file
        '''
        os.rename(file, "recordings/" + os.path.basename(file))

class Sound():
    sounds = {}
    '''
    Class that represents the soundbite associated with a particular phrase

    Class Variables:
        sounds(dict): stores all instantiated sounds

    Parameters:
        id(string): The unique identifier of the soundbite, typically the name of the associated phrase
        recording(string): The file name of a audio file in the recordings/ folder. The reocrding must be 0.25 second per syllable, i.e. equivalent to playing Chatusra Jati at 60 bpm
    '''
    def __init__(self, id, recording):
        self.id = id #Store the identifier
        self.recording = "recordings/" + recording #Store the recording
        Sound.sounds.update({id: self}) #We have created a new sound!

    def play(self):
        '''
        Plays the sound represented by this Sound object
        '''
        playsound(self.recording)

    @classmethod
    def merge(cls, sounds) -> str:
        '''
        For composite sounds, play all the sounds simultaneously

        Parameters:
            sounds(list[Sound]): the individual component sounds to play

        Returns:
            newRecording(string): An audio file containing the combination requested
        '''
        assert len(sounds) > 1, "More than 1 sound must be provided to merge"
        mergedSound = AudioSegment.from_file(sounds[0].recording)
        fileName = sounds[0].id
        for i in range(1, len(sounds)):
            mergedSound = mergedSound.overlay(AudioSegment.from_file(sounds[i].recording), position = 0)
            fileName += "+" + sounds[i].id
        fileName = "recordings/" + fileName + ".m4a"
        handler = mergedSound.export(fileName, format = "ipod")
        return fileName


    @classmethod
    def join(cls, sounds) -> str:
        '''
        For sequential sounds, play all the sounds one after the other, in the order given

        Parameters:
        sounds(list[Sound]): the individual component sounds to play

        Returns:
        newRecording(string): An audio file containing the combination requested
        '''
        assert len(sounds) > 1, "More than 1 sound must be provided to join"
        mergedSound = AudioSegment.from_file(sounds[0].recording)
        fileName = sounds[0].id
        for i in range(1, len(sounds)):
            mergedSound = mergedSound + AudioSegment.from_file(sounds[i].recording)
            fileName += sounds[i].id
        fileName = "recordings/" + fileName + ".m4a"
        handler = mergedSound.export(fileName, format = "ipod")
        return fileName

class Phrase():
    registeredPhrases = {} #The phrases that have been registered so far
    '''
    Class that represents a phrase on the tabla

    Parameters:
        mainID(string): The name of the phrase
        syllables(int): Number of syllables this phrase is
        position(string): Whether this phrase is played on the baiyan, daiyan, or both
        info(string): Information about how to play the phrase
        aliases(string): Other names for this phrase in compositions
        soundBite(Sound or string): Either "Fetch" if sound has been preregistered, or the path to an audio file, or a Sound object
        register(boolean): Whether this phrase should be registered
    '''
    def __init__(self, mainID, syllables = 1, position = 'baiyan', info = 'No info provided', aliases = None, soundBite = "Fetch", register = True):
        if not isinstance(soundBite, Sound) and soundBite != "Fetch":
            soundBite = Sound(mainID, soundBite) #We have a path to an audio file and need to convert it to a Sound object. The audio file should be in the recordings folder
        mainID = mainID.lower() #Lowercase all letters for consistency
        #Below, keep track of all possible names of the phrase
        self.ids = [mainID]
        if aliases:
            self.ids += aliases
        #Construct a description of the phrase for playing purposes
        self.description = "Phrase: " + str(self.ids) + "\nPlayed on " + position + ".\n" + info + "\n No. of syllables: " + str(syllables)
        #Set other class variables
        self.syllables = syllables
        self.position = position
        self.info = info
        self.soundBite = soundBite if soundBite != "Fetch" else Fetcher.fetch(mainID) #Fetch sound bite if needed
        if register:
            for id in self.ids:
                Phrase.registeredPhrases.update({id: self}) #Register the phrases by updating the static dictionary

    def __repr__(self):
        return str(self.ids[0]) #A phrase is uniquely represented by its name

    def play(self):
        self.soundBite.play() #Use the Sound instance's play method to play the phrase

    @classmethod
    def createCompositePhrase(cls, mainID, componentIDs, aliases = None, soundBite = "Fetch", register = True):
        '''
        Creates a composite phrase given component phrases

        Parameters:
            mainID(string): The name of the phrase
            componentIDs(list): IDs of the component phrases that make up this composite phrase
            aliases(string): Other names for this phrase in compositions
            soundBite(Sound or string): Either "Fetch" is sound has been preregistered, or the path to a MIDI .mid file, or a Sound object
            register(boolean): Whether this phrase should be registered

        Returns:
        x(Phrase): The sequential phrase
        '''
        assert len(componentIDs) == 2, "A composite phrase must have exactly 2 component phrases"
        assert componentIDs[0] in Phrase.registeredPhrases and componentIDs[1] in Phrase.registeredPhrases, "Must register component phrases first"
        component1 = Phrase.registeredPhrases[componentIDs[0]]
        component2 = Phrase.registeredPhrases[componentIDs[1]]
        assert component1.position != component2.position and component1.position in ["baiyan", "daiyan"] and component2.position in ["baiyan", "daiyan"], "Components must be played on different drums and cannot be composite components themselves. For components played in close succession on the same drum, see registerSequentialPhrase()"

        x = Phrase(mainID = mainID, syllables = max(component1.syllables, component2.syllables), position = "both drums", info = "Play the following two phrases simultaneously: \n1)" + component1.info + "\n2)" + component2.info, aliases = aliases, soundBite = soundBite if soundBite else fetch(mainID, "composite", componentIDs), register = register)
        if register:
            assert mainID in Phrase.registeredPhrases, "Registering composite phrase failed."
        return x

    @classmethod
    def createSequentialPhrase(cls, mainID, componentIDs, position, aliases = None, soundBite = "Fetch", register = True):
        '''
        Creates a sequential phrase given component phrases

        Parameters:
            mainID(string): The name of the phrase
            componentIDs(list): IDs of the sequential phrases that make up this composite phrase
            position(string): Whether this phrase is played on the baiyan, daiyan, or both
            aliases(string): Other names for this phrase in compositions
            soundBite(Sound or string): Either "Fetch" is sound has been preregistered, or the path to a MIDI .mid file, or a Sound object
            register(boolean): Whether this phrase should be registered

        Returns:
        x(Phrase): The sequential phrase
        '''
        assert all([id in Phrase.registeredPhrases for id in componentIDs]), "Must register component phrases first."
        syllables = 0
        info = "Play the following phrases in succession:"
        for i in range(len(componentIDs)):
            syllables += Phrase.registeredPhrases[componentIDs[i]].syllables
            info += "\n" + str(i) + ")" + Phrase.registeredPhrases[componentIDs[i]].info

        x = Phrase(mainID = mainID, syllables = syllables, position = position, info = info, aliases = aliases, soundBite = soundBite if soundBite else fetch(mainID, "sequential", componentIDs), register = register)
        if register:
            assert mainID in Phrase.registeredPhrases, "Registering sequential phrase failed."
        return x

class CompositionGenerator():
    #Class that provides a static method to generate a composition
    #Uses standard BolParser symbols (user can modify later)
    @classmethod
    def generate(cls, type:str, taal:Union[str, int], speedClass: str, jati: Union[str, int], school: str, token: str):
        '''
        A method that generates a composition given parameters using the Llama model available on HuggingFace

        Parameters:
            type(str): The type of composition to generate. Ex. Kayda, Palta, etc.
            taal(Union[str, int]): The taal of the composition. Ex. Teentaal or 16, Jhaptaal or 10, etc.
            speedClass(str): The speed class of the composition. Ex. Vilambit, Madhya, Drut
            jati(Union[str, int]): The jati of the composition, or the number of syllables per beat. Ex. Chatusra or 4, Tisra or 3
            school(str): The style of playing. Ex. Lucknow, Delhi, Ajrada, Punjabi, etc.
            token(str): The HuggingFace token for the user's access to Llama.
        '''
        warnings.warn("This is an experimental feature that may provide incorrect or incomplete results.")
        warnings.warn("Execution time might be excessive depending on your hardware.")
        TEMPLATE = '''
        {
        "composition": "Kayda",
        "name": "My Composition",
        "components":
          {"mainTheme":
           {"bhari": "dha ti ge ne | dha ti dha ge | dhin na ge na | tete ge ne | dha ti dha ge | dhin na ge na | tete tete | ge na tete | ge na dha ti | dha tete dha | ge ne dha ge | tin na ke na",
           "khali": "Infer"
           },
         "paltas": {
            "palta1": {
              "bhari": "dha ti ge ne | dha ti dha ge | dhin na ge na | tete ge ne | dha ti dha ge | dhin na ge na | dha ti ge ne | dha ti dha ge | dhin na ge na | tete ge ne | dha ti dha ge | dhin na ge na | dha ti ge ne | dha ti dha ge | dhin na ge na | tete ge ne | dha ti dha ge | dhin na ge na | tete tete | ge na tete | ge na dha ti | dha tete dha | ge ne dha ge | tin na ke na",
              "khali": "Infer"
            }
         },
         "tihai": "dha ti ge ne | dha ti dha ge | dhin na ge na | dha S S S | dhin na ge na | dha S S S | dhin na ge na | dha S S S | dha ti ge ne | dha ti dha ge | dhin na ge na | dha S S S | dhin na ge na | dha S S S | dhin na ge na | dha S S S | dha ti ge ne | dha ti dha ge | dhin na ge na | dha S S S | dhin na ge na | dha S S S | dhin na ge na | dha S S S"
         },
        "taal": "Ektaal",
        "speed": "60bpm",
        "jati": "Chatusra",
        "playingStyle": "Lucknow",
        "display": "Bhatkande"
        }
        '''
        phraseInfo = "The following phrases are defined by the user on the tabla, along with a description of how to play them: \n" + "\n".join([key + "." + val.description for key, val in Phrase.registeredPhrases.items()])
        mainPrompt = "Using the above phrases only, compose a " + type + " in taal with name/beats " + taal + " and speed class " + speedClass + ". The composition should be in jati with name/syllables per beat " + jati + " and in the " + school + " style of playing. Components of the composition should be marked appropriately."
        symbolPrompt = "Each beat should be separated with the character '|'. An example of the expected output if the user requests a Kayda of Ektaal, with Chatusra Jati, in the Lucknow Gharana is: \n" + TEMPLATE + "\n A phrase cannot span more than one beat. A phrase can also span exactly one syllable even if it usually spans more than one. In that case, enclose the phrase with parentheses."
        end = "Finally, in addition to following the above rules, the composition should be as authentic and aesthetically pleasing as possible."
        prompt = phraseInfo + mainPrompt + symbolPrompt + end
        messages = [
            {"role": "user", "content": prompt},
        ]
        pipe = pipeline("text-generation", model="meta-llama/Meta-Llama-3-70B-Instruct", token = token, torch_dtype=torch.float16, device_map="auto")
        return pipe(messages, do_sample = True, num_return_sequences = 1, eos_token_id = pipe.tokenizer.eos_token_id, return_full_text = False)[0]['generated_text']

class AudioToBolConvertor():
    #Class that provides a static method to transcribe a bol given the recording of a composition
    @classmethod
    def convert(cls, recording:str, speed:int, jati:int) -> str:
        '''
        A method that generates the bol given an audio recording

        Parameters:
            recording(str): The filename of the audio file
            speed(int): The speed, in beats per minute, in which the bol in the audio file is being played
            jati(int): The number of syllables per beat in the bol in the audio file

        Returns:
            bolString(str): THe transcription of the audio
        '''
        warnings.warn("This is an experimental feature that may provide incorrect or incomplete results.")
        currentSyllableDuration = 60.0/(speed*jati)
        desiredSyllableDuration = 0.25
        sound = AudioSegment.from_file(recording)
        if currentSyllableDuration > desiredSyllableDuration:
            sound = sound.speedup(currentSyllableDuration / desiredSyllableDuration)
        elif currentSyllableDuration < desiredSyllableDuration:
            sound = ae.speed_down(sound, currentSyllableDuration / desiredSyllableDuration)
        #Now, parse the audio for every 0.25 second snippet, comparing it with known recordings
        recordings = {val.soundBite.recording: key for key, val in Phrase.registeredPhrases}
        bolString = ""
        marker = 0
        while (marker < sound.duration_seconds * 1000):
            add = AudiotoBolConvertor.getMostSimilarSound(snippet = sound[marker: marker + 250], source = recordings)
            marker += Phrase.registeredPhrases[add].syllables * 250
            bolString += add
        return bolString

    @classmethod
    def getMostSimilarSound(cls, snippet, source:Dict[str, str]) -> str:
        '''
        A method that gets the most similar sounding bol to a given audio

        Parameters:
            snippet: The audio snippet to identify/transcribe
            from(dict<str, str>): The known vocabulary to choose from
        '''
        snippet.export("snippetTemp", format = "m4a")
        _, encoded = acoustid.fingerprint_file("snippetTemp")
        fingerprint, _ = chromaprint.decode_fingerprint(
            encoded
        )
        references = {}
        for key, val in source.items():
            _, e = acoustid.fingerprint_file(key)
            f, _ = chromaprint.decode_fingerprint(
                e
            )
            references[val] = f

        from operator import xor
        maxSimilarity = 0
        mostSimilarPhrase = None
        for phrase, print in references.items():
            max_hamming_weight = 32 * min(len(fingerprint), len(print))
            hamming_weight = sum(
                sum(
                    c == "1"
                    for c in bin(xor(fingerprint[i], print[i]))
                )
                for i in range(min(len(fingerprint), len(print)))
            )
            if (hamming_weight / max_hamming_weight) > maxSimilarity:
                maxSimilarity = hamming_weight / max_hamming_weight
                mostSimilarPhrase = phrase
        return mostSimilarPhrase


expansionarySchema = {
    "type": "object",
    "properties": {
        "mainTheme": {
            "type": "object",
            "properties":{
                "bhari": {"type": "string"},
                "khali": {"type": "string"},
            },
        },
        "paltas":{
            "type": "array",
            "items": {
                "type": "object",
                "properties":{
                    "bhari": {"type": "string"},
                    "khali": {"type": "string"},
                },
            },
        },
        "tihai": {"type": "string"},
    },
    "required": ["mainTheme", "paltas", "tihai"]
}


def expansionaryAssembler(tablaFile:SimpleNamespace) -> list[str]:
    result = []
    result.append(tablaFile.mainTheme.bhari)
    if tablaFile.mainTheme.khali == "Infer":
        result.append(BolParser.toKhali(tablaFile.mainTheme.bhari))
    else:
        result.append(tablaFile.mainTheme.khali)

    for palta in tablaFile.paltas:
        result.append(palta.bhari)
        if palta.khali == "Infer":
            result.append(BolParser.toKhali(palta.bhari))
        else:
            result.append(palta.khali)

    result.append(tablaFile.tihai)
    return result

fixedSchema = {
    "type": "object",
    "properties": {
        "content": {"type": "string"},
        "tihai": {"type": "string"},
    },
    "required": ["content"],
}


def fixedAssembler(tablaFile:SimpleNamespace) -> list[str]:
    result = []
    result.append(tablaFile.content)
    if hasattr(tablaFile, tihai):
        result.append(tablaFile.tihai)

    return result

chakradarSchema = {
    "type": "object",
    "properties": {
        "content": {"type": "string"},
        "tihai": {"type": "string"},
    },
    "required": ["content", "tihai"],
}


def chakradarAssembler(tablaFile:SimpleNamespace) -> list[str]:
    result = []
    result.append(tablaFile.content)
    result.append(tablaFile.tihai)
    return result

tihaiSchema = {
    "type": "object",
    "properties": {
        "content": {"type": "string"},
    },
    "required": ["content"],
}


def tihaiAssembler(tablaFile:SimpleNamespace) -> list[str]:
    result = []
    result.append(tablaFile.content)
    return result


def expansionaryValidityCheck(bol:Bol) -> bool:
    return True


def regularFixedValidityCheck(bol:Bol) -> bool:
    return True


def regularChakradarValidityCheck(bol:Bol) -> bool:
    phraseList = [phrase for phrase in bol.beats.phrases.keys()]
    k, m = divmod(len(phraseList), 3)
    cycles = (phraseList[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(3))
    return len(phraseList) % 3 and set(cycles[0]) == set(cycles[1]) and set(cycles[1]) == set(cycles[2])

def specialChakradarValidityCheck(bol:Bol) -> bool:
    return regularChakradarValidityCheck(bol) and all([beat.saam for beat in bol.markedBeats])

def regularTihaiValidityCheck(bol:Bol) -> bool:
    return regularChakradarValidityCheck(bol)

def bedamTihaiValidityCheck(bol:Bol) -> bool:
    phraseList = [phrase for phrase in bol.beats.phrases.keys()]
    return regularTihaiValidityCheck(bol) and all(["S" not in phrase.ids for phrase in phraseList])

def damdarTihaiValidityCheck(bol:Bol) -> bool:
    phraseList = [phrase for phrase in bol.beats.phrases.keys()]
    return regularTihaiValidityCheck(bol) and any(["S" in phrase.ids for phrase in phraseList])

def toRecursiveNamespace(d):
    x = SimpleNamespace()
    _ = [setattr(x, k,
                 toRecursiveNamespace(v) if isinstance(v, dict)
                 else [toRecursiveNamespace(e) for e in v] if isinstance(v, list)
                 else v) for k, v in d.items()]
    return x

class BolParser():
    '''
    Class that parses a .tabla file and converts it to a concise, playable form
    '''
    BEAT_DIVIDER = "|"
    PHRASE_SPLITTER = "-"
    PHRASE_JOINER_OPEN = "["
    PHRASE_JOINER_CLOSE = "]"
    MARKER = "~"

    SYMBOLSMD = '''
    <table>
      <tr>
        <th>Symbol</th>
        <th>Description</th>
        <th>Example + Walkthrough</th>
      </tr>
      <tr>
        <td><code>|</code></td>
        <td>This differentiates 2 beats.</td>
        <td><code>dha S S | ge na ge</code></td>
      </tr>
      <tr>
        <td><code>-</code></td>
        <td>indicates a sequential phrase needs to be split differently when conforming to a particular jati</td>
        <td><code>dha tere-kite | dhe tete</code>
        <br>
        While normally terekite would be automatically parsed as 4 syllables (as in terekite | dha ti ge ne) or 1 syllable (as in terekite dha ti dha | S ki te ta), here we need to specify it is 2 syllables to maintain Tisia Jati. This is necessary when there is no clear way to uphold the jati for the particular beat. Notice that we do not need to write tete in the second beat as te-te because it is by default 2 syllables, which along with the dhe, makes 3 syllables per beat.</td>
      </tr>
      <tr>
        <td><code>[]</code></td>
        <td>This is to group two phrases as 1 "syllable", so to speak, without creating a new sequential phrase.</td>
        <td><code>dha ti ge | [dha ge] tere-kite</code>
        <br>
        This indicates that dha & ge occupy the space normally taken by one syllable, again ensuring 3 syllables per beat - the 3 syllables in the second beat are [dha ge], tere, and kite, with the latter two part of the same sequential phrase (see - symbol definition above). Technically, this is equivalent to increasing the speed for a fraction of the beat, but the speed parameter in .tabla files is only for whole number of beats.</td>
      </tr>
      <tr>
        <td><code>~</code></td>
        <td>This is to indicate a specific phrase for further checks.</td>
        <td><code>dha ~ti ge | dha dha ti</code>
        <br>
        This singles out the first ti for further checks, such as those passed into the CompositionType for ensuring validity of a composition. An example of such a function would be to return <code>True</code> if the specified ti is the second syllable of its beat, and <code>False</code> otherwise.</td>
      </tr>
    </table>
    '''

    #Download recordings folder if it does not exist already
    destination = Path.cwd() / "recordings"
    destination.mkdir(exist_ok=True, parents=True)
    fs = fsspec.filesystem("github", org="shreyanmitra", repo="Tabalchi")
    fs.get(fs.ls("recordings/"), destination.as_posix(), recursive=True)

    #Register bhari-khali mappings, basic vocab, composite phrases, compositions, jatis, sequences, speeds, and taals
    vocabInitializer = [('ge', 1, 'baiyan', 'Use the index and middle fingers to strike the narrow part of the maidan above the shyahi', ['ga', 'ghet', 'gat'], Sound("ge", "Ge.m4a"), True),
    ('ke', 1, 'baiyan', 'With a flat palm, lift the front fingers and lay them down again on the maidan above the shyahi', ['ki', 'ka'], Sound("ke", "Ke.m4a"), True),
    ('kat', 1, 'baiyan', 'With a flat palm, lift the entire hand  and lay it back down on the drum', None, Sound("kat", "Di.m4a"), True),
    ('ghen', 1, 'baiyan', 'Use the index and middle fingers to strike the narrow part of the maidan above the shyahi, like in \'ge\'. Immediately lift the hand to allow reverb.', None, Sound("ghen", "Ghen.m4a"), True),
    ('na', 1, 'daiyan', "Use the index finger to strike the kinar while keeping the middle and ring fingers on the border between the shyahi and tha maidan", None, Sound("na", "Na.m4a"), True),
    ('ta', 1, 'daiyan', "Use the ring finger to vertically strike the border between the shyahi and tha maidan. Let your index finger bounce on the kinar to create a ringing effect", None, Sound("ta", "Ta.m4a"), True),
    ('tin', 1, 'daiyan', "Use the index finger and gently hit the shyahi, lifting immediately afterwards to create a high-pitched ringing effect", None, Sound("tin", "Tin.m4a"), True),
    ('thun', 1, 'daiyan', "Use the index finger and strongly hit the shyahi, lifting immediately afterwards to create a loud high-pitched ringing effect", None, Sound("thun", "Thun.m4a"), True),
    ('te', 1, 'daiyan', "Use the middle and ring fingers to slap the shyahi OR use the index finger to slap the shyahi. Do not lift the hand, creating a closed sound.", ['ti', 'tit', 'tet'], Sound("te", "Te.m4a"), True),
    ('ne', 1, 'daiyan', "Use the middle, ring, and pinky fingers to gently touch the border between the kinar and maidan. Let some reverb occur.", ['re', 'ra'], Sound("ne", "Ne.m4a"), True),
    ('di', 1, 'daiyan', "Use all fingers to strike the shyahi, and immediately lift, leading to a ringing sound.", None, Sound("di", "Di.m4a"), True),
    ('tere', 2, 'daiyan', "Swipe your thumb and other fingers alternately on the kinar above the shyahi (with your palm on the shyahi) for a swishing sound", None, Sound("tere", "Tere.m4a"), True),
    ('tete', 2, 'daiyan', "Use the middle and ring fingers to slap the shyahi and then use the index finger to slap the shyahi as well. Do not lift the hand, creating a closed sound.", None, Sound("tete", "Tete.m4a"), True),
    ('s', 1, 'both', "Silence", None, Sound("S", "S.m4a"), True)]
    for element in vocabInitializer:
        Phrase(*element)

    compositeInitializer = [('dha', ['ge', 'na'], None, Sound("dha", "Dha.m4a")),
    ('dhin', ['ge', 'tin'], ['gran'], Sound("dhin", "Dhin.m4a")),
    ('dhet', ['ge', 'tet'], ['dhe'], Sound("dhet", "Dhet.m4a")),
    ('dhere', ['ge', 'tere'], None, Sound("dhere", "Dhere.m4a")),
    ('dhete', ['ge', 'tete'], None, Sound("dhete", "Dhete.m4a")),
    ('kre', ['kat', 'te'], None, Sound("kre", "Kre.m4a")),
    ('kran', ['ke', 'ta'], None, Sound("kran", "Kran.m4a"))]
    for element in compositeInitializer:
        Phrase.createCompositePhrase(*element)

    sequentialInitializer = [('terekite', ['tete', 'ki', 'te'], "both", None, Sound("terekite", "Terekite.m4a")),
    ('gadigene', ['ga', 'di', 'ge', 'ne'], "both", None, Sound("gadigene", "Gadigene.m4a")),
    ('nagetete', ['na', 'ge', 'tete'], "both", None, Sound("nagetete", "Nagetete.m4a")),
    ('kitetaka', ['ki', 'tete', 'ka'], "both", None, Sound("kitetaka", "Kitetaka.m4a")),
    ('dheredhere', ['dhere', 'dhere'], "both", None, Sound("dheredhere", "Dheredhere.m4a")),
    ('teretere', ['tere', 'tere'], "daiyan", None, Sound("teretere", "Teretere.m4a"))]
    for element in sequentialInitializer:
        Phrase.createSequentialPhrase(*element)

    speedInitializer = [(lambda x: x <=60, random.randint(0, 60), "Vilambit"),
    (lambda x: x>60 and x<=120, random.randint(60,120), "Madhya"),
    (lambda x: x>120, random.randint(120,300), "Drut")
    ]
    for element in speedInitializer:
        SpeedClasses(*element)

    bhariKhaliMappings = {
    Phrase.registeredPhrases["dha"]:Phrase.registeredPhrases["ta"],
    Phrase.registeredPhrases["ge"] : Phrase.registeredPhrases["ke"],
    Phrase.registeredPhrases["dhin"] : Phrase.registeredPhrases["tin"],
    Phrase.registeredPhrases["dhete"] : Phrase.registeredPhrases["tete"],
    Phrase.registeredPhrases["dheredhere"] : Phrase.registeredPhrases["teretere"],
    Phrase.registeredPhrases["gran"] : Phrase.registeredPhrases["kran"]
    }

    taalInitializer = [{'beats':3, 'name':'Sadanand', 'taali':[1], 'khali':[]},
    {'beats':6, 'name':'Carnatic Rupaak', 'taali':[1,3], 'khali':[]},
    {'beats':6, 'name':'Dadra', 'taali':[1], 'khali':[4], 'theka':"dha|dhin|na|dha|tin|na"},
    {'beats':7, 'name':'Pashto', 'taali':[1,4,6], 'khali':[], 'theka':"tin|S|terekite|dhin|S|dha|ge"},
    {'beats':7, 'name':'Tevra', 'taali':[1,4,6], 'khali':[], 'theka':"dha|dhin|ta|tete|ka ta|ga di|ge ne"},
    {'beats':7, 'name':'Antarkrida', 'taali':[1,3,5], 'khali':[]},
    {'beats':7, 'name':'Rupaak', 'taali':[4,6], 'khali':[1], 'theka':"tin|tin|na|dhin|na|dhin|na na"},
    {'beats':8, 'name':'Keherwa', 'taali':[1], 'khali':[5], 'theka':"dha|ge|na|tin|na|ke|dhin|na"},
    {'beats':8, 'name':'Kawwali', 'taali':[1,5], 'khali':[]},
    {'beats':8, 'name':'Jat1', 'taali':[1,3,7], 'khali':[5]},
    {'beats':8, 'name':'Dhumali', 'taali':[1,3,7], 'khali':[5], 'theka':"dhin|dhin|dha|tin|terekite|dhin|dha ge|terekite"},
    {'beats':8, 'name':'Bhajni Theka', 'taali':[1], 'khali':[5]},
    {'beats':9, 'name':'Matta1', 'taali':[1,3,7,8], 'khali':[5]},
    {'beats':9, 'name':'Basant', 'taali':[1,2,3,4,6,8], 'khali':[5,7,9], 'theka':"dha|dhin|ta|dhet|ta|tete|ka ta|ga di|ge ne"},
    {'beats':9, 'name':'Anka', 'taali':[1,3,7], 'khali':[]},
    {'beats':9, 'name':'Jhap Sawari', 'taali':[1, 3, 8], 'khali':[6], 'theka':"dhin|na|dhin|dhin|na|ka ta|dhin dhin|na dhin|dhin na"},
    {'beats':9.5, 'name':'Sunand', 'taali':[1,3,8,9], 'khali':[6]},
    {'beats':9.5, 'name':'Kalawati', 'taali':[1,3,7.5], 'khali':[5]},
    {'beats':10, 'name':'At', 'taali':[1,4,7], 'khali':[9]},
    {'beats':10, 'name':'Sul Phaakta', 'taali':[1,5,7], 'khali':[3,9]},
    {'beats':10, 'name':'Sulfakta', 'taali':[1,3,5,8], 'khali':[]},
    {'beats':10, 'name':'Ukshav', 'taali':[1,5,7,9], 'khali':[3]},
    {'beats':10, 'name':'Kapaalabhruta', 'taali':[1,4,7], 'khali':[2,6]},
    {'beats':10, 'name':'Sul', 'taali':[1,5,7], 'khali':[3,9], 'theka':"dha|dha|dhin|ta|ki te|dha|tete|ka ta|ga di|ge ne"},
    {'beats':10, 'name':'Jhaptaal', 'taali':[1, 3, 8], 'khali':[6], 'theka':"dhin|na|dhin|dhin|na|tin|na|dhin|dhin|na"},
    {'beats':10.5, 'name':'Sardha Rupaak', 'taali':[1,5,8], 'khali':[]},
    {'beats':11, 'name':'Iktaali', 'taali':[1,5,7]},
    {'beats':11, 'name':'Rudra', 'taali':[1,3,4,5,7,8,9], 'khali':[], 'theka':"dha|tet|dha|terekite|dhin|na|terekite|thun|na|kat|ta"},
    {'beats':11, 'name':'Mani', 'taali':[1,4,9], 'khali':[6]},
    {'beats':11, 'name':'Indraleen', 'taali':[1,4,6,9], 'khali':[2]},
    {'beats':11, 'name':'Char Taal Ki Sawari', 'taali':[1, 3, 7, 9, 10], 'khali':[5]},
    {'beats':11, 'name':'Kumbha', 'taali':[1, 3, 4, 5, 7, 8, 9, 10], 'khali':[2, 6, 11], 'theka':"dha|dhin na|ta ka|tete|dha|ghe re|na ga|tete|ka ta|ga di|ge ne"},
    {'beats':11, 'name':'Ashtamangal1', 'taali':[1, 3, 4, 6, 7, 9, 10, 11], 'khali':[2, 5, 8], 'theka':"dhin|na|dhin|dhin|na|dhin|dhin|na|dha ge|na dha|terekite"},
    {'beats':12, 'name':'Uday', 'taali':[1,6,8], 'khali':[]},
    {'beats':12, 'name':'Chautaal', 'taali':[1,5,9,11], 'khali':[3,7], 'theka':"dha|dha|dhin|ta|ki te|dha|dhin|ta|tete|ka ta|ga di|ge ne"},
    {'beats':12, 'name':'Vikram', 'taali':[1,3,9], 'khali':[6]},
    {'beats':12, 'name':'Ektaal', 'taali':[1,5,9,11], 'khali':[3,7], 'theka':"dhin|dhin|dha ge|terekite|thun|na|kat|ta|dha ge|terekite|dhin|na"},
    {'beats':12, 'name':'Khemta', 'taali':[1, 4, 10], 'khali':[7], 'theka':"dha|te|dhin|na|tin|na|ta|te|dhin|na|dhin|na"},
    {'beats':13, 'name':'Jai', 'taali':[1,3,7,11,12], 'khali':[5,9]},
    {'beats':13, 'name':'Arnima', 'taali':[1,3,10,12], 'khali':[8]},
    {'beats':13, 'name':'Lilawati', 'taali':[1, 5, 9, 12], 'khali':[], 'theka':"dhin|dhin|dha|terekite|dhin|S|tin|tin|ta|terekite|dhin|dhin"},
    {'beats':14, 'name':'Dhamar', 'taali':[1,6,11], 'khali':[8], 'theka':"ka|dhe|te|dhe|te|dha|S|ga|te|te|te|te|ta|S"},
    {'beats':14, 'name':'At', 'taali':[1,6,11,13], 'khali':[4,9]},
    {'beats':14, 'name':'Deepchandi', 'taali':[1,4,11], 'khali':[8], 'theka':"dha|dhin|S|dha|dha|tin|S|ta|tin|dha|dha|dhin|S"},
    {'beats':14, 'name':'Jhoomra', 'taali':[1,4,11], 'khali':[8], 'theka':"dhin|S dha|terekite|dhin|dhin|dha ge|terekite|tin|S ta|terekite|dhin|dhin|dha ge|terekite"},
    {'beats':14, 'name':'Ada Chautaal', 'taali':[1,3,7,11], 'khali':[5,9,13], 'theka':"dhin|terekite|dhin|na|thun|na|kat|ta|terekite|dhin|na|dhin|dhin|na"},
    {'beats':14, 'name':'Brahma1', 'taali':[1, 3, 4, 6, 7, 8, 10, 11, 12, 13], 'khali':[2, 5, 9,14], 'theka':"dha|tet|dhet|dhin na|na ke|dhet|dhet|dhin na| na ke|dha ge|tete|ka ta|ga di|ge ne"},
    {'beats':14, 'name':'Pharudasta', 'taali':[1, 5, 9, 11, 13], 'khali':[3, 7], 'theka':"dhin|dhin|dha ge|terekite|thun|na|kat|ta|dhin na|ka dha|terekite|dhin na|ka dha|terekite"},
    {'beats':15, 'name':'Pancham Sawari', 'taali':[1,4,12], 'khali':[8], 'theka':"dhin|na|dhin dhin|ka ta|dhin dhin|na dhin|dhin na|tin S S kra|tin na|terekite|thun na|kat ta|dhin dhin|na dhin|dhin na"},
    {'beats':15, 'name':'Choti Sawari', 'taali':[1,5,9,13], 'khali':[], 'theka':"dha|S|dha|di|ga|na|dhin|na|ki|ta|ta|ka|di|na|ta"},
    {'beats':15, 'name':'Gaja Jhampaa', 'taali':[1,5,13], 'khali':[9], 'theka':"dha|dhin na|na ka|ta ka|dha|dhin na|na ka|ta ka|tin|na ka|ta ka|tete|ka ta|ga di|ge ne"},
    {'beats':15, 'name':'Indra', 'taali':[1,5,9,11,13], 'khali':[]},
    {'beats':15.5, 'name':'Yog', 'taali':[1,5,14], 'khali':[9]},
    {'beats':16, 'name':'Aryaa', 'taali':[1,3,7,10,13], 'khali':[]},
    {'beats':16, 'name':'Ikwai', 'taali':[1,5,13], 'khali':[9], 'theka':"dha|S|ge|ge|dha|ge|S|ge|ta|S|ke|ke|dha|ge|S|ghe"},
    {'beats':16, 'name':'Chachar', 'taali':[1,5,13], 'khali':[9]},
    {'beats':16, 'name':'Gajarmukh', 'taali':[1,6,8,13], 'khali':[11]},
    {'beats':16, 'name':'Teentaal', 'taali':[1,5,13], 'khali':[9], 'theka':"dha|dhin|dhin|dha|dha|dhin|dhin|dha|dha|tin|tin|ta|tete|dhin|dhin|dha"},
    {'beats':16, 'name':'Tilwada', 'taali':[1,5,13], 'khali':[9], 'theka':"dha|terekite|dhin|dhin|dha|dha|tin|tin|ta|terekite|tin|tin|dha|dha|dhin|dhin"},
    {'beats':16, 'name':'HaunsVilas', 'taali':[1,6,11,14], 'khali':[8]},
    {'beats':16, 'name':'Punjabi', 'taali':[1,5,13], 'khali':[9], 'theka':"dha|S dhin|na ka|dha|dha|S dhin|na ka|dha|dha|S tin|na ka|ta|ta|S dhin|na ka|dha"},
    {'beats':16, 'name':'Ushakiran', 'taali':[1,7,11], 'khali':[15]},
    {'beats':16, 'name':'Udeerna', 'taali':[1,8,10], 'khali':[]},
    {'beats':16, 'name':'Tappe ka Taal', 'taali':[1,5,13], 'khali':[9], 'theka':"dhin|S|dha|S ga|dha|dhin|ta|S kra|tin|S|ta|ga|dha|dhin|ta|S kra"},
    {'beats':16, 'name':'Addha', 'taali':[1,5,13], 'khali':[9]},
    {'beats':16, 'name':'Bari Sawari', 'taali':[1, 5, 9, 11, 13], 'khali':[3, 7, 15], 'theka':"dhin|na|dhin|na|dhin dhin|dhin na|dhin dhin|dhin na|ta S tere-kite|thun na|ta S tere-kite|thun na|kat ta S S|tere-kite dhin na|ge ne dha ge|na dha tere-kite"},
    {'beats':16, 'name':'Jat2', 'taali':[1,5,13], 'khali':[9], 'theka':"dha|S|dhin|S|dha|dha|tin|S|ta|S|tin|S|dha|dha|dhin|S"},
    {'beats':16, 'name':'Sitarkhani', 'taali':[1, 5, 13], 'khali':[9], 'theka':"dha|S dhin|S ka|dha|dha|S dhin|S ka|dha|dha|S ti|S ka|ta|ta|S dhe|S ka|dha"},
    {'beats':17, 'name':'Shikhar', 'taali':[1,13,15], 'khali':[7], 'theka':"dha|terekite|dhin na|na ka|thun|ga|dhin na|na ka|dhin na|ki ta|ta ka|dhet|dha|tete|ka ta|ga di|ge ne"},
    {'beats':17, 'name':'Sujan Shikhar', 'taali':[1,3,10,13,15], 'khali':[7]},
    {'beats':17, 'name':'Indraleen', 'taali':[1,8,13], 'khali':[4, 16]},
    {'beats':17, 'name':'Dhruvataal', 'taali':[1,6,8,13], 'khali':[]},
    {'beats':17, 'name':'Vishnu1', 'taali':[1, 5, 7, 11, 13, 15], 'khali':[], 'theka':"dha|S|ki|te|ta|ka|dhin|na|ki|te|ta|ka|dhe|S|dhin|na|ta"},
    {'beats':17, 'name':'Vishnu2', 'taali':[1, 3, 7, 11, 13, 15], 'khali':[], 'theka':"dha|S|ki|te|ta|ka|dhin|na|ki|te|ta|ka|dhe|S|dhin|na|ta"},
    {'beats':17, 'name':'Vishnu3', 'taali':[1, 3, 6, 10], 'khali':[14], 'theka':"dhin|na|dhin|dhin|na|dhin|terekite|dhin|na|dhin|dhin|na|dhin|dhin|na|dhin|na"},
    {'beats':17, 'name':'Vishnu4', 'taali':[1, 5, 9, 11, 13, 15], 'khali':[3, 7], 'theka':"dhin|terekite|dhin|na|thun|na|kat|ta|terekite|dhin|na|dha ge|na dha|terekite|dha ge|na dha|terekite"},
    {'beats':17, 'name':'Churamani', 'taali':[1, 4, 6, 10, 14], 'theka':"dha|ka|ta|thun|na|dhin|dhin|na|terekite|na|dhin|dhin|na|dhin|terekite|dhin|na"},
    {'beats':17, 'name':'Mayur', 'taali':[1, 3, 7, 13], 'khali':[], 'theka':"dha|dha|dhin na|na ka|dhe|dhe|dhin na|na ka|ki|te|ta|ka|ga|di|ge|ne|ta"},
    {'beats':18, 'name':'At2', 'taali':[1,8,15,17], 'khali':[5,11]},
    {'beats':18, 'name':'Matta2', 'taali':[1, 5, 7, 11, 13, 15], 'khali':[3, 9, 17], 'theka':"dha|S|ghe|re|na|ka|ghe|re|na|ka|te|te|ka|ta|ga|di|ga|ne"},
    {'beats':18, 'name':'Lakshmi', 'taali':[1,2,3,5,6,7,9,10,11,12,13,14,15,16,17], 'khali':[4, 8, 18], 'theka':"dhin na|dhin dha|terekite|dhin na|dhin dha|terekite|dha dha|terekite|dha dha|terekite|dhin na|dhin dha|terekite|thun na|ki re na ga|ta ge|ta S|terekite"},
    {'beats':18, 'name':'Ganesh', 'taali':[1,5,9,13,15], 'khali':[], 'theka':"dha|S|dhin|ta|dhin|ta|dha|S|dha|S|ki|ta|ta|ka|dha|dhi|ga|na"},
    {'beats':19, 'name':'Panchanan', 'taali':[1,3,9,11,15], 'khali':[6,18]},
    {'beats':19, 'name':'Shesh', 'taali':[1, 5, 9, 11, 13, 17, 18], 'khali':[], 'theka':"dha|S|ki|ta|ta|ka|dhin|na|ki|te|ta|ka|dha|S|ta|S|dha|ga di|ge ne"},
    {'beats':20, 'name':'Abhinandan', 'taali':[1,5,7,11,13,15,19], 'khali':[]},
    {'beats':20, 'name':'Arjun', 'taali':[1,5,7,11,13,15], 'khali':[]},
    {'beats':22, 'name':'Ashtamangal2', 'taali':[1,5,7,11,13,17,19,21], 'khali':[], 'theka':"dha|S|ki|te|ta|ka|dhin|na|ki|te|ta|ka|dhe|S|ta|S|ta|ka|dha|dhi|ga|na"},
    {'beats':22, 'name':'At3', 'taali':[1, 10, 19, 21], 'khali':[7,17]},
    {'beats':24, 'name':'Chaktaal', 'taali':[1,7,19], 'khali':[13]},
    {'beats':24, 'name':'Abhiram', 'taali':[1,7,10,14,19], 'khali':[]},
    {'beats':24, 'name':'At4', 'taali':[1,3,5,9,11,15], 'khali':[]},
    {'beats':24, 'name':'Kandarpa', 'taali':[1,3,5,9,17], 'khali':[13, 21]},
    {'beats':27, 'name':'Ardhya', 'taali':[1,5,7,9,14,17,22,23,24,25,26,27], 'khali':[]},
    {'beats':28, 'name':'Brahma2', 'taali':[1,5,7,11,13,15,19,21,23,25], 'khali':[3,9,17,27], 'theka':"dha|S|ta|S|dha|S|dhi|na|ta|ki|ta|dha|S|dhin|S|ta|S|dha|S|te|te|ka|ta|ga|di|ga|na"}]

    for element in taalInitializer:
        Taal(**element)

    jatiInitializer = [{'syllables':3, 'name':'Tisra'},
    {'syllables':4, 'name':'Chatusra'},
    {'syllables':5, 'name':'Khanda'},
    {'syllables':7, 'name':'Mishra'},
    {'syllables':9, 'name':'Sankeerna'}]

    for element in jatiInitializer:
        Jati(**element)

    compositionsInitializer = [("Kayda", expansionarySchema, expansionaryValidityCheck, expansionaryAssembler),
    ("Rela", expansionarySchema, expansionaryValidityCheck, expansionaryAssembler),
    ("Peshkar", expansionarySchema, expansionaryValidityCheck, expansionaryAssembler),
    ("GatKayda", expansionarySchema, expansionaryValidityCheck, expansionaryAssembler),
    ("LadiKayda", expansionarySchema, expansionaryValidityCheck, expansionaryAssembler),
    ("Gat", fixedSchema, regularFixedValidityCheck, fixedAssembler),
    ("Tukda", fixedSchema, regularFixedValidityCheck, fixedAssembler),
    ("GatTukda", fixedSchema, regularFixedValidityCheck, fixedAssembler),
    ("Chakradar", fixedSchema, regularChakradarValidityCheck, chakradarAssembler),
    ("FarmaisiChakradar", chakradarSchema, specialChakradarValidityCheck, chakradarAssembler),
    ("KamaaliChakradar", chakradarSchema, specialChakradarValidityCheck, chakradarAssembler),
    ("Paran", fixedSchema, regularFixedValidityCheck, fixedAssembler),
    ("Aamad", fixedSchema, regularFixedValidityCheck, fixedAssembler),
    ("Chalan", fixedSchema, regularFixedValidityCheck, fixedAssembler),
    ("GatParan", fixedSchema, regularFixedValidityCheck, fixedAssembler),
    ("Kissm", fixedSchema, regularFixedValidityCheck, fixedAssembler),
    ("Laggi", fixedSchema, regularFixedValidityCheck, fixedAssembler),
    ("Mohra", fixedSchema, regularFixedValidityCheck, fixedAssembler),
    ("Mukhda", fixedSchema, regularFixedValidityCheck, fixedAssembler),
    ("Rou", fixedSchema, regularFixedValidityCheck, fixedAssembler),
    ("Tihai", tihaiSchema, regularTihaiValidityCheck, tihaiAssembler),
    ("Bedam Tihai", tihaiSchema, bedamTihaiValidityCheck, tihaiAssembler),
    ("Damdaar Tihai", tihaiSchema, damdarTihaiValidityCheck, tihaiAssembler)]

    for element in compositionsInitializer:
        CompositionType(*element)

    @classmethod
    def toKhali(cls, bolString:str) -> str:
        result = bolString
        for key, val in BolParser.bhariKhaliMappings.items():
            for id in key.ids:
                result = result.replace(id, val.ids[0])
        return result


    @classmethod
    def parse(cls, file) -> Bol:
        assert ".tabla" in file, "Please pass a valid .tabla file"
        with open(file, 'r') as composition:
            rawData = json.load(composition)
            data = SimpleNamespace(**rawData)
        try:
            compositionType = CompositionType.registeredTypes[data.type]
            taal = Taal.registeredTaals[data.taal]
            speed = {}
            if isinstance(data.speed, dict):
                for key, val in data.speed.items():
                    speed.update({BeatRange.fromString(key): Speed(val)})
            else:
                speed = Speed(data.speed)
            jati = {}
            if isinstance(data.jati, dict):
                for key, val in data.speed.items():
                    jati.update({BeatRange.fromString(key): Jati.registeredJatis[val]})
            elif isinstance(data.jati, str) and data.jati != "Infer":
                jati = Jati.registeredJatis[data.jati]
            else:
                jati = data.jati
            playingStyle = data.playingStyle
            assert data.display in Notation.VALID_NOTATIONS
            display = eval(data.display)
            assert compositionType.preCheck(data.components)
        except Exception:
            raise ValueError("Something is wrong with the configuration of your .tabla file")

        data = toRecursiveNamespace(rawData)
        segmentList = compositionType.assembler(data.components)
        if(any([(segment.count(BolParser.BEAT_DIVIDER) + 1) % taal.beats != 0 for segment in segmentList])):
            warnings.warn("Specific segments of your composition do not align with the selected taal. This may or may not be a problem, depending on the type of composition. The program will continue without error as long as the entire composition as a whole aligns in number of beats with the taal.")
        completeBolString = BolParser.BEAT_DIVIDER.join(segmentList)
        completeBolStringFormatted = completeBolString.split(BolParser.BEAT_DIVIDER)
        for index in range(len(completeBolStringFormatted)):
            if (index+1) % taal.beats == 1:
                completeBolStringFormatted[index] = '\n\n\033[1m' + completeBolStringFormatted[index] + '\033[0m'
        completeBolStringFormatted = BolParser.BEAT_DIVIDER.join(completeBolStringFormatted)
        assert (completeBolString.count(BolParser.BEAT_DIVIDER) + 1) % taal.beats == 0, "Taal not compatible with composition. The composition: \n" + completeBolStringFormatted + "\n\n has " + str(completeBolString.count(BolParser.BEAT_DIVIDER) + 1) + " beats, which is not a multiple of " + str(taal.beats) + "."
        totalBeats = completeBolString.count(BolParser.BEAT_DIVIDER) + 1
        beatPartition = completeBolString.split(BolParser.BEAT_DIVIDER)
        if isinstance(speed, dict):
            assert BeatRange.isContiguousSequence(list(speed.keys()), totalBeats)
        if isinstance(jati, dict):
            assert BeatRange.isContiguousSequence(list(jati.keys()), totalBeats)

        def inferJati(beat:str) -> int:
            beat = beat.strip()
            newStr = ""
            inGrouping = False
            for char in beat:
                if char == BolParser.PHRASE_JOINER_OPEN:
                    inGrouping = True
                if char == BolParser.PHRASE_JOINER_OPEN:
                    inGrouping =  False

                if char == " " and inGrouping:
                    newStr += "*"
                elif char == BolParser.PHRASE_SPLITTER:
                    newStr += " "
                else:
                    newStr += char

            return len(newStr.split(" "))


        def getJati(beatNumber:int) -> int:
            if isinstance(jati, Jati):
                return jati.syllables
            elif isinstance(jati, dict):
                for beatInterval in jati.keys():
                    if beatNumber >= beatInterval.begin and beatNumber < beatInterval.end:
                        return jati[beatInterval].syllables
            else:
                return -1 #Control flow should never end up here

        def getSpeed(beatNumber:int) -> int:
            if isinstance(speed, Speed):
                return speed.bpm
            elif isinstance(speed, dict):
                for beatInterval in speed.keys():
                    if beatNumber >= beatInterval.begin and beatNumber < beatInterval.end:
                        return speed[beatInterval].bpm
            else:
                return -1 #Control flow should never end up here

        finalizedBeats = []
        for i in range (len(beatPartition)):
            beat = beatPartition[i]
            #assert jati == "Infer" or inferJati(beat) == getJati(i + 1), "Provided jati for certain beats does not match actual jati at beat " + str(i) + ". User-specified jati: " + str(getJati(i+1)) + " syllables per beat, while actual jati seems to be " + str(inferJati(beat)) + " syllables per beat. The bols in the beat are: " + beat + "."
            beat = beat.strip()
            newStr = ""
            inGrouping = False
            for char in beat:
                if char == BolParser.PHRASE_JOINER_OPEN:
                    inGrouping = True
                if char == BolParser.PHRASE_JOINER_OPEN:
                    inGrouping =  False

                if char == " " and inGrouping:
                    newStr += "*"
                else:
                    newStr += char

            intermediate = newStr.split(" ")
            markers = []
            rawPhrases = []
            syllableCount = []

            for elem in intermediate:
                if(not elem.startswith(BolParser.PHRASE_JOINER_OPEN)):
                    if(elem.startswith(BolParser.MARKER)):
                        markers.append(1)
                    else:
                        markers.append(0)
                    correspondingPhrase = Phrase.registeredPhrases[elem.replace(BolParser.PHRASE_SPLITTER, "").replace(BolParser.MARKER, "")]
                    rawPhrases.append(correspondingPhrase)
                    if elem.count(BolParser.PHRASE_SPLITTER) != 0:
                        syllableCount.append(elem.count(BolParser.PHRASE_SPLITTER) + 1)
                    else:
                        syllableCount.append(correspondingPhrase.syllables)
                else:
                    deconstructed = (elem.replace(BolParser.PHRASE_JOINER_OPEN, "").replace(BolParser.PHRASE_JOINER_CLOSE, "")).split("*")
                    for subElem in deconstructed:
                        if(subElem.startswith(BolParser.MARKER)):
                            markers.append(1)
                        else:
                            markers.append(0)
                        correspondingPhrase = Phrase.registeredPhrases[subElem.replace(BolParser.PHRASE_SPLITTER, "").replace(BolParser.MARKER, "")]
                        rawPhrases.append(correspondingPhrase)
                        if subElem.count(BolParser.PHRASE_SPLITTER) != 0:
                            syllableCount.append((subElem.count(BolParser.PHRASE_SPLITTER) + 1) / len(deconstructed))
                        else:
                            syllableCount.append((correspondingPhrase.syllables) / len(deconstructed))

            assert jati == "Infer" or sum(syllableCount) == getJati(i + 1), "Provided jati for certain beats does not match actual jati at beat " + str(i) + ". User-specified jati: " + str(getJati(i+1)) + " syllables per beat, while actual jati seems to be " + str(sum(syllableCount)) + " syllables per beat. The bols in the beat are: " + beat + "."
            taaliKhaliOrNone = 0
            if (i + 1)%taal.beats in taal.taali:
                taaliKhaliOrNone = 1
            elif (i + 1)%taal.beats in taal.khali:
                taaliKhaliOrNone = -1
            saam = False
            if i%taal.beats == 0:
                saam = True
            beatSpeed = getSpeed(i + 1)
            phraseSyllableMapping = list(zip(rawPhrases, syllableCount))
            try:
                finalizedBeats.append(Beat(i + 1, taaliKhaliOrNone, saam, phraseSyllableMapping, beatSpeed, markers))
            except Exception as e:
                raise AssertionError("Beat could not be initialized.\nDebug Info\n__________\n\nBeat Number: " + str(i + 1) + "\nBeat Speed: " + str(beatSpeed) + "\nMarkers: " + str(markers) + "\nPhrase-Syllable Mapping: " + str(phraseSyllableMapping) + "\nIntermediateString: " + str(intermediate))
        parsedResult = Bol(finalizedBeats)
        compositionType.mainCheck(parsedResult)
        return parsedResult


    @classmethod
    def getSymbolRules(cls):
        from rich.console import Console
        from rich.markdown import Markdown
        console = Console()
        md = Markdown(BolParser.SYMBOLSMD)
        console.print(md)

    @classmethod
    def getVocabInitializer(cls):
        return BolParser.vocabInitializer

    @classmethod
    def getCompositesInitializer(cls):
        return BolParser.compositeInitializer

    @classmethod
    def getSequentialInitializer(cls):
        return BolParser.sequentialInitializer

    @classmethod
    def getSpeedInitializer(cls):
        return BolParser.speedInitializer

    @classmethod
    def getJatiInitializer(cls):
        return BolParser.jatiInitializer

    @classmethod
    def getBhariKhaliMappings(cls):
        return BolParser.bhariKhaliMappings

    @classmethod
    def getTaalInitializer(cls):
        return BolParser.taalInitializer

    @classmethod
    def getCompositionsInitializer(cls):
        return BolParser.compositionsInitializer
