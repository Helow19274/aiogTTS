# aiogTTS [![PyPI version](https://img.shields.io/pypi/v/aiogTTS.svg)](https://pypi.org/project/aiogTTS/) [![Python versions](https://img.shields.io/pypi/pyversions/aiogTTS.svg)](https://pypi.org/project/aiogTTS/) [![Build Status](https://travis-ci.org/Helow19274/aiogTTS.svg?branch=master)](https://travis-ci.org/Helow19274/aiogTTS/)

**aiogTTS** (asynchronous Google Text-to-Speech), a Python library to interface with Google Translate's text-to-speech API.
Writes spoken mp3 data to a file or a file-like object (bytestring) for further audiomanipulation.

#### Original gTTS - <https://github.com/pndurette/gTTS/> (75% of this repo)

## Features
- Customizable speech-specific sentence tokenizer that allows for unlimited lengths of text to be read, all while keeping proper intonation, abbreviations, decimals and more;
- Customizable text pre-processors which can, for example, provide pronunciation corrections;

### Installation
```bash
$ pip install aiogTTS
```

### Quickstart
```python
import asyncio
from io import BytesIO
from aiogtts import aiogTTS


async def main():
    aiogtts = aiogTTS()
    io = BytesIO()
    await aiogtts.save('Привет, мир!', 'audio.mp3', lang='ru')
    await aiogtts.write_to_fp('Hallo!', io, slow=True, lang='de')


asyncio.get_event_loop().run_until_complete(main())
```
