# PyPI Release Notes

Notes and information on how to do the PyPI release for the SageMaker project. For full details on packaging you can reference this page
[Packaging](https://packaging.python.org/tutorials/packaging-projects/#packaging-your-project)

The following instructions should work, but things change :)

### Package Requirements

-   pip install tox
-   pip install \--upgrade setuptools wheel
-   pip install twine

### Setup pypirc

The easiest thing to do is setup a \~/.pypirc file with the following
contents

``` {.bash}
[distutils]
index-servers =
  pypi
  testpypi

[pypi]
repository=https://upload.pypi.org/legacy/
username=<pypi username>
password=<pypi password>

[testpypi]
repository=https://test.pypi.org/legacy/
username=<pypi username>
password=<pypi password>
```

### Tox Background

Tox will install the SageMaker Sandbox package into a blank virtualenv and then execute all the tests against the newly installed package. So if everything goes okay, you know the pypi package installed fine and the tests (which puls from the installed `sageworks` package) also ran okay.

### Make sure ALL tests pass

``` {.bash}
$ cd sageworks
$ tox 
```

If ALL the test above pass\...

### Clean any previous distribution files
```
make clean
```
### Tag the New Version
```
git tag v0.1.8 (or whatever)
git push --tags
```

### Create the TEST PyPI Release

``` {.bash}
python setup.py sdist bdist_wheel
twine upload dist/* -r testpypi
```

### Install the TEST PyPI Release

``` {.bash}
$ pip install --index-url https://test.pypi.org/simple sageworks
```

### Create the REAL PyPI Release

``` {.bash}
$ twine upload dist/* -r pypi
```

### Push any possible changes to Github

``` {.bash}
$ git push
```
