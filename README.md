# Tabalchi <img src="https://github.com/user-attachments/assets/0d47f705-74d9-43e4-91b0-a6c8806965ba" width=100/>


A parser for Indian classical music, specifically tabla. 

To get started, write a .tabla file with the *bol* (composition)

Example: 

```javascript
{
composition: "Kayda",
name: "My Composition", //Optional
components:
  {mainTheme:
   {bhari:
      "dha ti ge ne | dha ti dha ge | dhin na ge na\
      tete ge ne | dha ti dha ge | dhin na ge na\
      tete tete | ge na tete | ge na dha ti\
      dha tete dha | ge ne dha ge | tin na ke na",
   khali: "Infer"
   }
  },
 paltas:
  {...}, //Include paltas here
 tihai: "", //Include tihai here
taal: "Ektaal", //12 would work here too
speed: "60bpm", //optional
speedClass: "Vilambit",
speedExceptions:
 { ...}, //If certain parts of the bol are faster or slower, can put it here in the format {begin-end beat no.: speed}, etc.
jati: "Chatusra", //Indicates 4 syllables per beat
playingStyle: "Lucknow",
display: "Bhatkande", //Script to use: could be Bhatkande, Paluskar, or None
}
```

To play a given .tabla file, simply write the following Python code. You will need to first install the ``Tabla`` library through ``pip install Tabla``

```python
from Tabla import *
with open("yourBol.tabla", "r") as file:
  play(file)
```

To view the entire composition with the notation of your choice (specified in the .tabla file itself), simply write:

```python
from Tabla import *
with open("yourBol.tabla", "r") as file:
  write(file, "yourOutputFile.txt/pdf")
```

## About the Author
Shreyan has been learning the tabla for 12+ years at the [Akhil Bharatiya Gandharva Mahavidyalaya Mandal](https://en.wikipedia.org/wiki/Akhil_Bharatiya_Gandharva_Mahavidyalaya_Mandal). He is currently pursuing a Visharad (equivalent to a Bachelor's) certification.




