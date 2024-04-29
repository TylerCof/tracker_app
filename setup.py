from setuptools import find_packages, setup

setup(
    name="tracker",
    version="0.1",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    entry_points={
        "console_scripts": [
            "tracker=tracker.__main__:main",
        ]
    },
)
