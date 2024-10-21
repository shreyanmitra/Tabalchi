# Tabalchi <img src="https://github.com/user-attachments/assets/0d47f705-74d9-43e4-91b0-a6c8806965ba" width=100/>


A parser for Indian classical music, specifically tabla, that **does not** require any knowledge of MIDI, music sampling, or battery kits.

To get started, write a .tabla file with the *bol* (composition). The syntax of a .tabla file is identical to that of a .json file.

Example:

```javascript
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
```

To play a given .tabla file, simply write the following Python code. You will need to first install the ``Tabla`` library through ``pip install Tabla``

```python
from Tabla import *
parser = BolParser()
parser.load("yourBol.tabla")
parser.play()
```

To view the entire composition with the notation of your choice (specified in the .tabla file itself), simply write:

```python
from Tabla import *
parser = BolParser()
parser.load("yourBol.tabla")
parser.write("yourOutputFile.txt/pdf")
```
The parser above is the standard BolParser provided by the library. You can create your own parser by doing something like:

```python
from Tabla import*
#NOT RECOMMENDED
class MyParser(BolParser):
  #override functionality
parser = MyParser()
parser.load("yourBol.tabla")
```

However, this is not preferred. Instead, the standard parser uses a set of predefined configurations which can be updated through the ``Fetcher`` class' ``addFileToConfig()``. It also uses some standard symbols given below:

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

This symbol specification is given by ``BolParser``'s ``getSymbols()``, which should be overridden to return an appropriate markdown file if your parser uses different/additional symbols.

We now give brief descriptions of the main classes you may find yourself using. See the docs for more detailed descriptions.

1. Fetcher - Given a phrase, this class retrieves the corresponding Sound object. It also modifies the configuration files, or adds a new recording.
2. Sound - A wrapper around a MIDI file that offers ``play`` functionality and also keeps track of all valid Sound objects at a specific time of program execution.
3. Phrase - A class that represents a valid *bol* on the tabla. Associated with a sound and syllable count, among other properties.
4. Composition - A class that represents a composition. Properties include extensibility, components, speed, and jati.

## About the Author
Shreyan has been learning the tabla for 12+ years at the [Akhil Bharatiya Gandharva Mahavidyalaya Mandal](https://en.wikipedia.org/wiki/Akhil_Bharatiya_Gandharva_Mahavidyalaya_Mandal). He is currently pursuing a Visharad (equivalent to a Bachelor's) certification.
