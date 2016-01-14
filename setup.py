from setuptools import setup, find_packages
import zonemanager

setup(
    name='zonemanager',
    version=zonemanager.__version__,
    description='Simple Route53 zone management',
    packages=find_packages(),
    include_package_data=True,
    py_modules=['zonemanager'],
    install_requires=[
        'click',
        'pyyaml',
        'dnspython',
        'route53'
    ],
    entry_points={
        'console_scripts': ['manage = zonemanager.manager:cli']
    }
)
