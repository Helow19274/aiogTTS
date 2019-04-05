from setuptools import setup

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='aiogTTS',
    version='1.0',

    author='Helow19274',
    author_email='helow@helow19274.tk',

    description='A Python library to interface with Google Translate text-to-speech API',
    long_description=long_description,
    long_description_content_type='text/markdown',

    url='https://github.com/Helow19274/aiogTTS',
    packages=['aiogtts', 'aiogtts/tokenizer'],
    install_requires=['aiohttp', 'beautifulsoup4'],
    extras_require={'tests': ['pytest-asyncio']},

    classifiers=(
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Software Development :: Libraries',
        'Topic :: Multimedia :: Sound/Audio :: Speech'
    )
)
