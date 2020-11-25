from cms_search import __version__
from setuptools import setup

setup(
    name='django-cookie-alert',
    version=__version__,
    author='InQuant GmbH',
    author_email='info@inquant.de',
    packages=['cms_search'],
    url='https://github.com/InQuant/cms_search',
    license='MIT',
    description='App to add elastic search functionality for page-content to a django cms instance.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    zip_safe=False,
    include_package_data=True,
    package_data={'': ['README.md'], },
    install_requires=[],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django/DjangoCMS',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
