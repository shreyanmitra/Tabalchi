#(C) Shreyan Mitra

#Imports
import json #For parsing .tabla files
from config.initialize import * #For file configs
from abc import ABC, abstractmethod #For defining abstract classes
from playsound import playsound #For playing sounds
from pydub import AudioSegment #For merging and joining sounds
from typing import* #For type hints
from types import SimpleNamespace #For accessing dictionary field using dot notation
import os #For moving files
import warnings #For warnings

#For descriptions of the different types of tabla compositions, visit www.tablalegacy.com (not affiliated with this product or the author in any way)
#Sometimes, differences between types of compositions are hard to quantify, and come down to the "feel" of the composition.

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

    def range(self) -> int:
        '''
        Returns the number of beats represented by this beat range
        '''
        return self.end - self.begin

    @classmethod
    def isContiguousSequence(cls, ranges:List[BeatRange], totalBeats:int) -> bool:
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
        if(ranges[-1].end != totalBeats or ranges[0].begin != 1):
            return False
        return True

    @classmethod
    def getSubsequence(cls, ranges:List[BeatRange], begin:int, end:int) -> List[BeatRange]:
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
        return sorted(subsequence)

class Composition(ABC):
    '''
    Abstract class that represents a generic tabla composition.

    Required Properties:
        type(str): The class of composition (Ex. Kayda, Gat, etc.)
        name(str): The name of the composition
        components(list): Ordered collection of other components that make up this composition (Ex. Kayda = MainTheme + Paltas + Tihai)
        taal(Taal): The taal this composition is in (Ex. Teentaal, Pancham Sawadi), given as a Taal object
        speed(Speed or dict<BeatRange, Speed>): The speed of this composition, given as a Speed object. Can specify specific ranges if speed varies
        jati(Jati or dict<BeatRange, Speed>): The jati of this composition, given as a Jati object. This is the number of syllables per beat. Can specify specific ranges if jati varies
        playingStyle(String): The gharana, or style, of playing. As of the current version, this has no immediate effect and is only for information. If you want to make certain bols sound different, you need to record new MIDI files for them.
        display(Notation): The notation system to use when displaying the composition
        length(int): The length of the composition
    '''
    @property
    @abstractmethod
    def type(self):
        ...
    @property
    @abstractmethod
    def length(self):
        ...
    @property
    @abstractmethod
    def name(self):
        ...
    @property
    @abstractmethod
    def components(self):
        ...
    @property
    @abstractmethod
    def taal(self):
        ...
    @property
    @abstractmethod
    def speed(self):
        ...
    @property
    @abstractmethod
    def jati(self):
        ...
    @property
    @abstractmethod
    def playingStyle(self):
        ...
    @property
    @abstractmethod
    def display(self):
        ...

class ExtensibleComposition(Composition, ABC):
    '''
    An abstract class that inherits from Composition class. It has some additional properties.

    Required Properties:
        mainTheme(MainTheme): A MainTheme object that represents the main theme of the extensible composition, upon which other components are expanded from
        paltas(list[Palta]): A list of Palta objects that represent variations on the main theme
        tihai(Tihai): A Tihai object that represents the final component of the extensible composition
    '''
    @property
    @abstractmethod
    def mainTheme(self):
        ...
    @property
    @abstractmethod
    def paltas(self):
        ...
    @property
    @abstractmethod
    def tihai(self):
        ...

class PublicComposition(Composition, ABC):
    '''
    Abstract class that represents a composition that can be imported from a dot tabla file
    '''
    @classmethod
    @abstractmethod
    def fromdottabla(cls):
        ...

class ComponentComposition(Composition, ABC):
    '''
    Abstract class that represents a composition that cannot be imported from a dict
    '''
    @classmethod
    @abstractmethod
    def fromdict(cls):
        ...

class Kayda(ExtensibleComposition, PublicComposition):
    '''
    A class that represents a Kayda.

    Parameters:
        See properties of Composition and ExtensibleComposition
    '''
    def __init__(self, type:str, name:str, mainTheme:MainTheme, paltas:List[Palta], tihai:Tihai, taal:Taal, speed:Union[Speed, Dict[BeatRange, Speed]], jati:Union[Jati, Dict[BeatRange, Jati]], playingStyle:str, display:Notation):
        assert type == "Kayda", "Attempted to initialize " + type + " as Kayda"
        self._type = type
        self._name = name
        assert mainTheme._length % taal.beats == 0, "Provied main theme is not compatible with provided taal. Did you miss a | somewhere?"
        assert all(palta._length % taal.beats == 0 for palta in paltas), "Provied paltas are not compatible with provided taal. Did you miss a | somewhere?"
        assert tihai.length % taal.beats == 0, "Provied tihai is not compatible with provided taal. Did you miss a | somewhere?"
        self._mainTheme = mainTheme
        self._paltas = paltas
        self._tihai = tihai
        self._length = mainTheme._length + sum(palta._length for palta in paltas) + tihai._length
        self._taal = taal
        if isinstance(speed, dict):
            assert BeatRange.isContiguousSequence(list(speed.keys()), self._length), "Beat range specified does not cover the entire composition's length."
        self._speed = speed
        if isinstance(jati, dict):
            assert BeatRange.isContiguousSequence(list(jati.keys()), self._length), "Beat range specified does not cover the entire composition's length."
        self._jati = jati
        self._playingStyle = playingStyle
        self._display = display
        self._components = [mainTheme]
        self._components.extend(self._paltas)
        self._components.append(self._tihai)
        self._bol = mainTheme._bol
        for palta in self._paltas:
            self._bol += "| " + palta._bol
        self._bol += self._tihai._bol

    @classmethod
    def fromdottabla(cls, file):
        data = SimpleNamespace(**json.loads(file))
        mainTheme = MainTheme.fromdict(dict(data.components.mainTheme, speed = BeatRange.getSubsequence(self._speed, 1, self._mainTheme._length), jati = BeatRange.getSubsequence(self._jati, 1, self._mainTheme._length)))
        paltas = [Palta.fromdict(palta) for palta in data.components.paltas]
        tihai = Tihai.fromdict(data.components.tihai)
        return Kayda(data.composition, data.name, MainTheme.fromdict(data.components.mainTheme), [Palta.fromdict(palta) for palta in data.components.paltas], Tihai.fromdict(data.components.tihai), Taal(data.taal), Speed(data.speed) if not isinstance(data.speed, dict) else {BeatRange(key): Speed(val) for key, val in data.speed}, Jati(data.jati) if not isinstance(data.jati, dict) else {BeatRange(key): Jati(val) for key, val in data.jati}, data.playingStyle, Notation(data.display))

    def type(self):
        return self._type

    def length(self):
        return self._length

    def mainTheme(self):
        return self._mainTheme

    def paltas(self):
        return self._paltas

    def tihai(self):
        return self._tihai

    def name(self):
        return self._name

    def components(self):
        return self._components

    def taal(self):
        return self._taal

    def speed(self):
        return self._speed

    def jati(self):
        return self._jati

    def playingStyle(self):
        return self._playingStyle

    def display(self):
        return self._display

class Rela(ExtensibleComposition):
    '''
    A class that represents a Rela.

    Parameters:
        See properties of Composition and ExtensibleComposition
    '''
    def __init__(self, type:str, name:str, mainTheme:MainTheme, paltas:List[Palta], tihai:Tihai, taal:Taal, speed:Union[Speed, Dict[BeatRange, Speed]], jati:Union[Jati, Dict[BeatRange, Jati]], playingStyle:str, display:Notation):
        assert type == "Rela", "Attempted to initialize " + type + " as Rela"
        self._type = type
        self._name = name
        assert mainTheme._length % taal.beats == 0, "Provied main theme is not compatible with provided taal. Did you miss a | somewhere?"
        assert all(palta._length % taal.beats == 0 for palta in paltas), "Provied paltas are not compatible with provided taal. Did you miss a | somewhere?"
        assert tihai.length % taal.beats == 0, "Provied tihai is not compatible with provided taal. Did you miss a | somewhere?"
        self._mainTheme = mainTheme
        self._paltas = paltas
        self._tihai = tihai
        self._length = mainTheme._length + sum(palta._length for palta in paltas) + tihai._length
        self._taal = taal
        if isinstance(speed, dict):
            assert all(val.bpm > 120 for val in speed.values()), "Relas must have speeds greater than 120bpm (Madhya or Drut Laya)"
        else:
            assert speed.bpm > 120, "Relas must have speeds greater than 120bpm (Madhya or Drut Laya)"
        self._speed = speed
        self._jati = jati
        self._playingStyle = playingStyle
        self._display = display
        self._components = [mainTheme]
        self._components.extend(self._paltas)
        self._components.append(self._tihai)

    @classmethod
    def fromdottabla(cls, file):
        data = SimpleNamespace(**json.loads(file))
        return Rela(data.composition, data.name, MainTheme.fromdict(data.components.mainTheme), [Palta.fromdict(palta) for palta in data.components.paltas], Tihai.fromdict(data.components.tihai), Taal(data.taal), Speed(data.speed) if not isinstance(data.speed, dict) else {BeatRange(key): Speed(val) for key, val in data.speed}, Jati(data.jati) if not isinstance(data.jati, dict) else {BeatRange(key): Jati(val) for key, val in data.jati}, data.playingStyle, Notation(data.display))

    def type(self):
        return self._type

    def length(self):
        return self._length

    def mainTheme(self):
        return self._mainTheme

    def paltas(self):
        return self._paltas

    def tihai(self):
        return self._tihai

    def name(self):
        return self._name

    def components(self):
        return self._components

    def taal(self):
        return self._taal

    def speed(self):
        return self._speed

    def jati(self):
        return self._jati

    def playingStyle(self):
        return self._playingStyle

    def display(self):
        return self._display

class Peshkar(ExtensibleComposition):
    '''
    A class that represents a Rela.

    Parameters:
        See properties of Composition and ExtensibleComposition
    '''
    def __init__(self, type:str, name:str, mainTheme:MainTheme, paltas:List[Palta], tihai:Tihai, taal:Taal, speed:Speed, jati:Jati, playingStyle:str, display:Notation):
        self._type = type
        self._name = name
        self._mainTheme = mainTheme
        self._paltas = paltas
        self._tihai = tihai
        self._taal = taal
        assert speed.bpm < 120, "Peshkar speed should be less than 120 bpm (in Vilambit Laya)"
        self._speed = speed
        self._jati = jati
        self._playingStyle = playingStyle
        self._display = display
        self._components = [mainTheme]
        self._components.extend(self._paltas)
        self._components.append(self._tihai)

    @classmethod
    def fromdottabla(cls, file):
        data = SimpleNamespace(**json.loads(file))
        return Peshkar(data.composition, data.name, MainTheme.fromdict(data.components.mainTheme), [Palta.fromdict(palta) for palta in data.components.paltas], Tihai.fromdict(data.components.tihai), Taal(data.taal), Speed(data.speed) if not isinstance(data.speed, dict) else {BeatRange(key): Speed(val) for key, val in data.speed}, Jati(data.jati) if not isinstance(data.jati, dict) else {BeatRange(key): Jati(val) for key, val in data.jati}, data.playingStyle, Notation(data.display))


    def type(self):
        return self._type

    def mainTheme(self):
        return self._mainTheme

    def paltas(self):
        return self._paltas

    def tihai(self):
        return self._tihai

    def name(self):
        return self._name

    def components(self):
        return self._components

    def taal(self):
        return self._taal

    def speed(self):
        return self._speed

    def jati(self):
        return self._jati

    def playingStyle(self):
        return self._playingStyle

    def display(self):
        return self._display

class Uthaan(ExtensibleComposition):
    pass

class GatKayda(ExtensibleComposition):
    pass

class LadiKayda(ExtensibleComposition):
    pass

class FixedSizeComposition(Composition, ABC):
    @property
    @abstractmethod
    def content(self):
        ...

class Gat(FixedSizeComposition):
    @property
    @abstractmethod
    def tihai(self):
        ...

class Tukda(FixedSizeComposition):
    @property
    @abstractmethod
    def tihai(self):
        ...

class GatTukda(FixedSizeComposition):
    @property
    @abstractmethod
    def tihai(self):
        ...

class Chakradar(FixedSizeComposition):
    @property
    @abstractmethod
    def tihai(self):
        ...

class FarmaisiChakradar(FixedSizeComposition):
    @property
    @abstractmethod
    def tihai(self):
        ...

class KamaaliChakradar(FixedSizeComposition):
    @property
    @abstractmethod
    def tihai(self):
        ...

class Paran(FixedSizeComposition):
    pass

class Aamad(FixedSizeComposition):
    pass

class Chalan(FixedSizeComposition):
    pass

class GatParan(FixedSizeComposition):
    pass

class Kissm(FixedSizeComposition):
    pass

class Laggi(FixedSizeComposition):
    pass

class Mohra(FixedSizeComposition):
    pass

class Mukhda(FixedSizeComposition):
    pass

class Rou(FixedSizeComposition):
    pass

class Tihai(FixedSizeComposition):
    pass

class BedamTihai(Tihai):
    pass

class DamdarTihai(Tihai):
    pass

class MainTheme(FixedSizeComposition):
    pass

class Palta(FixedSizeComposition):
    pass

class Bhari(FixedSizeComposition):
    pass

class Khali(FixedSizeComposition):
    pass

class Numeric():
    pass

class Taal(FixedComposition, Numeric):
    pass

class Jati(Numeric):
    pass

class Speed(Numeric):
    pass

class Notation():
    pass

class Bhatkande(Notation):
    pass

class Paluskar(Notation):
    pass

class Theka(FixedSizeComposition):
    pass

class Bol(FixedSizeComposition):



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
            raise ValueError("Did not find soundbite. Have you preregistered the id? Otherwise, you should just pass the soundBite when initializing the phrase.")
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
    def addFileToConfig(cls, name, file):
        '''
        A method to add a .phrases file to the config folder and update .init

        Parameters:
            name(str): Name of the attribute to add to .init. Generally all caps
            file(str): Path to the file
        '''

        os.rename(file, "config/" + os.path.basename(file))
        with open("config/.init", "a") as file:
            file.write("\n" + name + " = " + os.path.basename(file))

        warnings.warn("Config files changed. If you initialized a parser module, you may need to re-initialize it to see changes.")



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
        recording(string): The file name of a audio file in the recordings/ folder
    '''
    def __init__(self, id, recording):
        self.id = id #Store the identifier
        self.recording = "recordings/" + recording #Store the recording
        sounds.update({id: self}) #We have created a new sound!

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
        if not isinstance(soundBite, Sounds) and soundBite != "Fetch":
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
        self.soundBite = soundBite if soundBite != "Fetch" else fetch(mainID) #Fetch sound bite if needed
        if register:
            for id in self.ids:
                Phrase.registeredPhrases.update({id: self}) #Register the phrases by updating the static dictionary

    def __repr__(self):
        return str(mainID) #A phrase is uniquely represented by its name

    def play(self):
        self.soundBite.play() #Use the Sound instance's play method to play the phrase



class CompositionGenerator(ABC):
    pass

class AudioToBolConvertor():
    


class BolParser():
    '''
    Class that parses a .tabla file and converts it to a concise, playable form
    '''
    def __init__(self):
        #Register a set of predetermined starter phases. Can be edited by modifying the config/ files
        self.initObject = Initializer()
        with open("config/" + self.initObject.VOCAB, "r") as file0:
            lines = file0.readlines()
            assert lines[0].strip() == "@VocabDefine", "Initializer Object was given malformed vocab definition file. Please check config/.init"
            for line in lines:
                if "@" not in line:
                    Phrase(*eval(line))

        with open("config/" + self.initObject.COMPOSITE, "r") as file1:
            lines = file1.readlines()
            assert lines[0].strip() == "@CompositeDefine", "Initializer Object was given malformed composite definition file. Please check config/.init"
            for line in lines:
                if "@" not in line:
                    self.createCompositePhrase(*eval(line))

        with open("config/" + self.initObject.SEQUENCE) as file2:
            lines = file2.readlines()
            assert lines[0].strip() == "@SequentialDefine", "Initializer Object was given malformed sequential definition file. Please check config/.init"
            for line in lines:
                if "@" not in line:
                    self.createSequentialPhrase(*eval(line))


    def createCompositePhrase(mainID, componentIDs, aliases = None, soundBite = "Fetch", register = True):
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

    def createSequentialPhrase(mainID, componentIDs, position, aliases = None, soundBite = "Fetch", register = True):
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
        assert id in Phrase.registeredPhrases for id in componentIDs, "Must register component phrases first."
        syllables = 0
        info = "Play the following phrases in succession:"
        for i in range(len(componentIDs)):
            syllables += Phrase.registeredPhrases[componentIDs[i]].syllables
            info += "\n" + str(i) + ")" + Phrase.registeredPhrases[componentIDs[i]].info

        x = Phrase(mainID = mainID, syllables = syllables, position = position, info = info, aliases = aliases, soundBite = soundBite if soundBite else fetch(mainID, "sequential", componentIDs), register = register)
        if register:
            assert mainID in Phrase.registeredPhrases, "Registering sequential phrase failed."
        return x

    def parse(self, file):
        assert ".tabla" in file, "Please pass a valid .tabla file"


    def convertBhariToKhali(self, bhari):
        pass
