# Tabalchi <img src="https://github.com/user-attachments/assets/0d47f705-74d9-43e4-91b0-a6c8806965ba" width=100/>


A parser for Indian classical music, specifically tabla, that **does not** require any knowledge of MIDI, music sampling, or battery kits.

<blockquote>
Note that this is a brand-new library that is not necessarily stable. Feel free to provide feedback to the author
</blockquote>

To get started, write a .tabla file with the *bol* (composition). The syntax of a .tabla file is identical to that of a .json file.

Example:

```javascript
{
"type": "Kayda",
"name": "My Composition",
"components":
  {"mainTheme":
   {"bhari": "dha ti ge ne | dha ti dha ge | dhin na ge na | tete ge ne | dha ti dha ge | dhin na ge na | tete tete | ge na tete | ge na dha ti | dha tete dha | ge ne dha ge | tin na ke na",
   "khali": "Infer"
   },
 "paltas": [
    {
      "bhari": "dha ti ge ne | dha ti dha ge | dhin na ge na | tete ge ne | dha ti dha ge | dhin na ge na | dha ti ge ne | dha ti dha ge | dhin na ge na | tete ge ne | dha ti dha ge | dhin na ge na | dha ti ge ne | dha ti dha ge | dhin na ge na | tete ge ne | dha ti dha ge | dhin na ge na | tete tete | ge na tete | ge na dha ti | dha tete dha | ge ne dha ge | tin na ke na",
      "khali": "Infer"
    }
 ],
 "tihai": "dha ti ge ne | dha ti dha ge | dhin na ge na | dha s s s | dhin na ge na | dha s s s | dhin na ge na | dha s s s | dha ti ge ne | dha ti dha ge | dhin na ge na | dha s s s | dhin na ge na | dha s s s | dhin na ge na | dha s s s | dha ti ge ne | dha ti dha ge | dhin na ge na | dha s s s | dhin na ge na | dha s s s | dhin na ge na | dha s s s"
 },
"taal": "Ektaal",
"speed": 60,
"jati": "Chatusra",
"playingStyle": "Lucknow",
"display": "Bhatkande"
}
```
First, make sure required dependencies are in your system as follows:

```bash
sudo apt install ffmpeg acoustid-fingerprinter
```

To play a given .tabla file, simply write the following Python code. You will need to install the ``Tabla`` library through ``pip install Tabla``

```python
from Tabla import *
parser = BolParser()
parser.parse("yourBol.tabla").play()
```

To view the entire composition with the notation of your choice (specified in the .tabla file itself), simply write:

```python
from Tabla import *
parser = BolParser()
parser.parse("yourBol.tabla").write("yourOutputFile.txt/pdf", Bhatkande)
```
The parser above is the standard BolParser provided by the library. You can create your own parser by doing something like:

```python
from Tabla import*
class MyParser(BolParser):
  #override functionality
parser = MyParser()
parser.load("yourBol.tabla")
```

The standard parser uses a set of predefined configurations available through the appropriate ``get`` methods. It also uses some standard symbols given below:

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

This symbol specification is given by ``BolParser``'s ``getSymbols()``, which should be overridden to return appropriate markdown text if your parser uses different/additional symbols.

We now give brief descriptions of the main classes you may find yourself using in addition to BolParser. See the [docs](https://shreyanmitra.github.io/Tabalchi/) for more detailed descriptions.

1. **BeatRange**: Represents an interval of beats with methods for checking sequences and subsequences.
2. **CompositionType**: Defines a composition type with a schema, validity check, and registration for future use.
3. **Numeric**: An abstract base class representing entities with an associated number, utilized for Taal, Jati, and Speed classes.
4. **Taal**: Represents a rhythmic cycle or meter in Indian classical music, storing beats, clap positions, and additional information.
5. **Jati**: Represents a rhythmic grouping or subdivision, defined by the number of syllables.
6. **SpeedClasses**: Categorizes speed into classes based on beats per minute with methods for checking and generating random speeds.
7. **Speed**: Represents a specific tempo, either by beats per minute or by a named speed class.
8. **Notation**: An abstract base class for converting a Bol into a string format, with a method for displaying the notation.
9. **Bhatkande**: Intended to handle Bhatkande notation (without current implementation).
10. **Paluskar**: Intended to handle Paluskar notation (without current implementation).
11. **Bol**: Represents a collection of beats with methods for playback and writing to a file using a specified notation.
12. **Beat**: Represents a collection of phrases within a beat, managing playback and phrase duration calculations.
13. **Fetcher**: Provides static methods for fetching sound data associated with phrases or adding new audio recordings.
14. **Sound**: Represents the soundbite associated with a phrase, with methods for playing and merging or joining sounds.
15. **Phrase**: Represents a tabla phrase including its properties, soundbite, and functionality for playing and creating composite or sequential phrases.
16. **CompositionGenerator**: Offers a static method for generating a composition of a specified type using a machine learning model.
17. **AudioToBolConvertor**: Provides a static method to transcribe a Bol from an audio recording based on speed and jati.

## About the Author
Shreyan has been learning the tabla for 12+ years at the [Akhil Bharatiya Gandharva Mahavidyalaya Mandal](https://en.wikipedia.org/wiki/Akhil_Bharatiya_Gandharva_Mahavidyalaya_Mandal). He is currently pursuing a Visharad (equivalent to a Bachelor's) certification.
