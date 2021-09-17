"""Functions for working with DICOM value representations."""
from typing import Union

from pydicom.valuerep import PersonName


def check_person_name(person_name: Union[str, PersonName]) -> None:
    """Check for problems with person name strings.

    The DICOM Person Name (PN) value representation has a specific format with
    multiple components (family name, given name, middle name, prefix, suffix)
    separated by caret characters ('^'), where any number of components may be
    missing and trailing caret separators may be omitted. Unfortunately it is
    both easy to make a mistake when constructing names with this format, and
    impossible to check for certain whether it has been done correctly.

    This function checks for strings representing person names that have a high
    likelihood of having been encoded incorrectly and raises an exception if
    such a case is found.

    A string is considered to be an invalid person name if it contains no caret
    characters.

    Note
    ----
    A name consisting of only a family name component (e.g. ``'Bono'``) is
    valid according to the standard but will be disallowed by this function.
    However if necessary, such a name can be still be encoded by adding a
    trailing caret character to disambiguate the meaning (e.g. ``'Bono^'``).

    Parameters
    ----------
    person_name: Union[str, pydicom.valuerep.PersonName]
        Name to check.

    Raises
    ------
    ValueError
        If the provided value is highly likely to be an invalid person name.
    TypeError
        If the provided person name has an invalid type.

    """
    if not isinstance(person_name, (str, PersonName)):
        raise TypeError('Invalid type for a person name.')

    name_url = (
        'http://dicom.nema.org/dicom/2013/output/chtml/part05/'
        'sect_6.2.html#sect_6.2.1.2'
    )
    if '^' not in person_name and person_name != '':  # empty string is allowed
        raise ValueError(
            f'The string "{person_name}" is unlikely to represent the '
            'intended person name since it contains only a single component. '
            'Construct a person name according to the format in described '
            f'in {name_url}, or, in pydicom 2.2.0 or later, use the '
            'pydicom.valuerep.PersonName.from_named_components() method '
            'to construct the person name correctly. If a single-component '
            'name is really intended, add a trailing caret character to '
            'disambiguate the name.'
        )