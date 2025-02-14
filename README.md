# Python Dash Template

1. Rename the `package_name` directory
2. Ensure `import package_name as proj` on line 7 of `app.py` is updated to reflect the new directory name
3. Update `name='package_name'` on line 8 of `setup.py` to reflect the new directory name
4. Ensure `app.py` and `setup.py` are saved
5. Optionally create and activate a virtual environment
6. `pip install -e .`
7. `python server.py`