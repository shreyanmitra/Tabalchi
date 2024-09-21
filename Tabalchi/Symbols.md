# Meaning of Symbols:

*This is the symbol specification for the default provided BolParser class. You can create your own parser, but it must: (1) inherit BolParser and (2) implement a new Symbols.md file if it changes the maning of any of the symbols / adds symbols / removes symbols.*


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
    <td><code>dha tere-kite | dhe tete.</code>
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
</table>
