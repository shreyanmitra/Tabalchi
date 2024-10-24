from setuptools import setup, find_namespace_packages

setup(name='Tabalchi',
      version='0.0.9',
      description='Tabalchi: Parser and Generator for Indian Classical Music',
      long_description=open("README.md", "r", encoding="utf-8").read(),
      long_description_content_type="text/markdown",
      keywords="music midi indian-music, audio-transcription",
      url="https://github.com/shreyanmitra/Tabalchi",
      author = "Shreyan Mitra",
      install_requires=[
        "jsonschema",
        "playsound",
        "pydub",
        "audio_effects",
        "pyacoustid",
        "pychromaprint",
        "typing",
        "pathlib",
        "transformers",
        "torch",
        "fsspec",
        "rich"
      ],
      include_package_data=True,
      package_data={'': ['static/*']},
      packages=["Tabalchi"],
      )
