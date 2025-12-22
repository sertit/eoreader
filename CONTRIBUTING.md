# Contribute

## Report issues

Issue tracker: https://github.com/sertit/eoreader/issues

Please check that a similar issue does not already exist and include the following information in your post:

- Describe what you expected to happen.
- If possible, include a [minimal reproducible example](https://stackoverflow.com/help/minimal-reproducible-example)
  to help us identify the issue. This also helps check that the issue is not with your own code.
- Describe what actually happened. Include the full traceback if there was an exception.
- List your Python and EOReader versions.
  If possible, check if this issue is already fixed in the latest releases or the latest code in the repository.

## Submit patches

If you intend to contribute to **EOReader** source code:

```
conda env create -f environment.yml
conda activate -n eoreader
pre-commit install
```

or

```
pip install -r requirements.txt
pre-commit install
```

Note that to run the documentation, you have to add this step:

```
pip install -r requirements-doc.txt
```


We use `pre-commit` to run a suite of linters, formatters and pre-commit hooks (`black`, `isort`, `flake8`) to
ensure the code base is homogeneously formatted and easier to read. It's important that you install it, since we run the
exact same hooks in the Continuous Integration.

For now, you won't be able to run the test suite as we cannot provide an example of each product (some are licensed). We
will take care of that for you. Please be sure that your code is running on Python 3.9+.

## Release EOReader

Releases are made by tagging a commit on the master branch. To make a new release,

* Ensure you correctly updated `README.md` and `CHANGES.md`
* Check that the version string in `eoreader/__meta__.py` (the variable `__version__`) is correctly updated
* Push your local master branch to remote.

### Update notebooks

* Run the notebooks in a dedicated docker container that points to the data.
* Be sure you have the latest version of EOReader installed (why not installing it in editable mode) `pip install -e /home/data/_EXTRACTEO/eoreader`
* `cd /home/data/_EXTRACTEO/eoreader`
* Run sphinx (here with 14 CPUs) `sphinx-build docs docs/_build/html -E -j 14`
* Zip the `eoreader/docs/_build.jupyter_cache` folder 
* Place it where the path given by the `JUPYTER_CACHE_URL` environment variable points (used in the `readthedocs.yml` file)