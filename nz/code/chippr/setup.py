from setuptools import setup

setup(
    name="chippr",
    version="0.1",
    author="Alex Malz",
    author_email="aimalz@nyu.edu",
    url = "https://github.com/aimalz/chippr",
    packages=["chippr"],
    description="Cosmological Hierarchical Inference with Probabilistic Photometric Redshifts",
    long_description=open("README.md").read(),
    package_data={"": ["README.md", "LICENSE"]},
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        ],
    install_requires=["matplotlib", "numpy", "scipy"]
)
