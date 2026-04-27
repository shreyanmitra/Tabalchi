from pathlib import Path
from setuptools import setup


README = Path(__file__).parent / "README.md"


setup(
    name="Tabalchi",
    version="0.0.9",
    description="Tabalchi: Parser and Generator for Indian Classical Music",
    long_description=README.read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    keywords="tabla, indian-classical-music, audio, parser",
    url="https://github.com/shreyanmitra/Tabalchi",
    author="Shreyan Mitra",
    license="MIT",
    python_requires=">=3.9",
    install_requires=[
        "jsonschema",
        "playsound",
        "pydub",
        "audio_effects",
        "fsspec",
        "rich",
    ],
    extras_require={
        "ml": [
            "transformers",
            "torch",
        ],
        "transcription": [
            "pyacoustid",
            "pychromaprint",
        ],
        "full": [
            "transformers",
            "torch",
            "pyacoustid",
            "pychromaprint",
        ],
        "dev": [
            "build",
            "twine",
            "ruff",
        ],
    },
    include_package_data=True,
    package_data={"": ["static/*"]},
    packages=["Tabalchi"],
    project_urls={
        "Homepage": "https://github.com/shreyanmitra/Tabalchi",
        "Documentation": "https://shreyanmitra.github.io/Tabalchi/",
        "Source": "https://github.com/shreyanmitra/Tabalchi",
        "Issues": "https://github.com/shreyanmitra/Tabalchi/issues",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Software Development :: Libraries",
    ],
)
