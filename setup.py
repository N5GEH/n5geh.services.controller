from setuptools import setup, find_packages

setup(
    name='controller4fiware',
    version='0.1.0',
    packages=find_packages(),
    description='Cloud-based controller framework '
                'for FIWARE platform',
    author='RWTH Aachen University, E.ON Energy Research Center, Institute\
        of Energy Efficient Buildings and Indoor Climate',
    author_email='junsong.du@eonerc.rwth-aachen.de',
    install_requires=[
        'python-dotenv~=1.0.0',
        'filip~=0.3.0'
        # Add any other dependencies your package requires
    ],
    entry_points={
        'console_scripts': [
            'your_script_name = your_package_name.controller:main'
        ]
    },
    python_requires=">=3.8"
)
