
# lite-text-tools

\[ 
**☞☞☞ This is the readme for a project from the
[simple-modern-poetry](https://github.com/jlevy/simple-modern-poetry)
template.**
Fill it in and delete this message!
Below are brief instructions on setup and development workflows that you may
use or modify for your project.
\]

## Installing Python, pipx, and Poetry

Sadly, there are many, many ways to install and set up your Python environment, each
with its own pitfalls.

This is a quick cheat sheet for one of the simplest and most reliable ways to set up
**Python 3.11+** and **Poetry 2.0+** (what you should use as of 2025) using
[**pyenv**](https://github.com/pyenv/pyenv) and
[**pipx**](https://github.com/pypa/pipx).

For macOS:

```shell
brew update
brew install pyenv pipx
```

For Ubuntu:

```shell
curl https://pyenv.run | bash
apt install pipx
```

Now you can install a current Python and Poetry:

```shell
pyenv install 3.13.2  # Pick the version you want.
pipx install poetry  # Or use `pipx upgrade poetry` if you've done this before.
```

For Windows or other platforms, see the pyenv and poetry instructions. 

## Development

For development workflows, see [development.md](development.md).

* * *

*This project was built from
[simple-modern-poetry](https://github.com/jlevy/simple-modern-poetry).*