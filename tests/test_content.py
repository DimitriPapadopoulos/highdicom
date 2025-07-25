import datetime
from unittest import TestCase

import pytest
from pydicom import dcmread
from pydicom.dataset import Dataset
from pydicom.sr.codedict import codes
from pydicom.sr.coding import Code
from pydicom.data import get_testdata_file, get_testdata_files

import numpy as np

from highdicom.enum import UniversalEntityIDTypeValues
from highdicom.sr import CodedConcept
from highdicom import (
    __version__,
    IssuerOfIdentifier,
    PaletteColorLUT,
    ContentCreatorIdentificationCodeSequence,
    ContributingEquipment,
    ModalityLUT,
    ModalityLUTTransformation,
    LUT,
    PaletteColorLUTTransformation,
    PixelMeasuresSequence,
    PlaneOrientationSequence,
    PlanePositionSequence,
    ReferencedImageSequence,
    RescaleTypeValues,
    SpecimenCollection,
    SpecimenDescription,
    SpecimenPreparationStep,
    SpecimenProcessing,
    SpecimenSampling,
    UID,
    SpecimenStaining,
    VOILUT,
    VOILUTTransformation,
    VOILUTFunctionValues,
)
from highdicom.sr.value_types import (
    CodeContentItem,
    TextContentItem,
    DateTimeContentItem
)

from .utils import write_and_read_dataset


class TestContentCreatorIdentification(TestCase):

    def setUp(self):
        super().setUp()
        self._person_codes = [codes.DCM.Person, codes.DCM.Technologist]
        self._institution_name = 'MGH'
        self._person_address = '1000 Main St.'
        self._person_telephone_numbers = ['123456789']
        self._email = 'example@example.com'
        self._institution_address = '123 Broadway'
        self._institution_code = CodedConcept(
            value='1',
            meaning='MGH',
            scheme_designator='HOSPITAL_NAMES',
        )
        self._department_name = 'Radiology'
        self._department_code = codes.SCT.RadiologyDepartment

    def test_construction_minimal(self):
        creator_id = ContentCreatorIdentificationCodeSequence(
            person_identification_codes=self._person_codes,
            institution_name=self._institution_name,
        )
        assert len(creator_id) == 1
        creator_id_item = creator_id[0]
        assert creator_id_item.InstitutionName == self._institution_name
        for code1, code2 in zip(
            creator_id_item.PersonIdentificationCodeSequence,
            self._person_codes
        ):
            assert code1.CodeValue == code2.value

    def test_construction_full(self):
        creator_id = ContentCreatorIdentificationCodeSequence(
            person_identification_codes=self._person_codes,
            institution_name=self._institution_name,
            person_address=self._person_address,
            person_telephone_numbers=self._person_telephone_numbers,
            person_telecom_information=self._email,
            institution_code=self._institution_code,
            institution_address=self._institution_address,
            institutional_department_name=self._department_name,
            institutional_department_type_code=self._department_code,
        )
        assert len(creator_id) == 1
        creator_id_item = creator_id[0]
        assert creator_id_item.InstitutionName == self._institution_name
        for code1, code2 in zip(
            creator_id_item.PersonIdentificationCodeSequence,
            self._person_codes
        ):
            assert code1.CodeValue == code2.value
        assert creator_id_item.PersonAddress == self._person_address
        assert (
            creator_id_item.PersonTelephoneNumbers ==
            self._person_telephone_numbers[0]
        )
        assert (
            creator_id_item.PersonTelecomInformation ==
            self._email
        )
        assert (
            creator_id_item.InstitutionCodeSequence[0].CodeValue ==
            self._institution_code.value
        )
        assert creator_id_item.InstitutionAddress == self._institution_address
        assert (
            creator_id_item.InstitutionalDepartmentName ==
            self._department_name
        )
        department_code = \
            creator_id_item.InstitutionalDepartmentTypeCodeSequence[0]
        assert (department_code.CodeValue == self._department_code.value)


class TestContributingEquipment:

    def test_basic(self):
        item = ContributingEquipment(
            manufacturer='Foo Inc',
            purpose_of_reference=codes.DCM.ModifyingEquipment,
        )

        assert item.Manufacturer == 'Foo Inc'
        assert (
            item.PurposeOfReferenceCodeSequence[0].CodeValue ==
            codes.DCM.ModifyingEquipment.value
        )

    def test_full(self):
        item = ContributingEquipment(
            manufacturer='Foo Inc',
            purpose_of_reference=codes.DCM.AcquisitionEquipment,
            manufacturer_model_name='Foo Scanner',
            software_versions='v1.0',
            device_serial_number='12345',
            institution_name='General Hospital',
            institutional_department_name='Radiology',
            institution_address='123 Hospital Ave',
            station_name='Scanner Bay 1',
            contribution_datetime=datetime.datetime(year=2000, month=1, day=1),
            contribution_description='Image acquisition equipment',
        )

        assert isinstance(item, ContributingEquipment)
        assert item.Manufacturer == 'Foo Inc'
        assert (
            item.PurposeOfReferenceCodeSequence[0].CodeValue ==
            codes.DCM.AcquisitionEquipment.value
        )
        assert item.ManufacturerModelName == 'Foo Scanner'
        assert item.SoftwareVersions == 'v1.0'
        assert item.DeviceSerialNumber == '12345'
        assert item.InstitutionName == 'General Hospital'
        assert item.InstitutionalDepartmentName == 'Radiology'
        assert item.StationName == 'Scanner Bay 1'
        assert item.ContributionDescription == 'Image acquisition equipment'
        assert (
            item.ContributionDateTime ==
            datetime.datetime(year=2000, month=1, day=1)
        )

    def test_highdicom(self):
        item = ContributingEquipment.for_highdicom()

        assert isinstance(item, ContributingEquipment)
        assert item.Manufacturer == 'Highdicom open-source contributors'
        assert item.ManufacturerModelName == 'highdicom'
        assert item.SoftwareVersions == __version__

    @pytest.mark.parametrize(
        'f',
        [
            get_testdata_file('eCT_Supplemental.dcm'),
            get_testdata_file('examples_jpeg2k.dcm'),
            get_testdata_file('MR_small.dcm'),
            get_testdata_file('JPEG2000.dcm'),
            get_testdata_file('CT_small.dcm'),
        ]
    )
    def test_for_source_image(self, f):
        dcm = dcmread(f)
        item = ContributingEquipment.for_image_acquisition(dcm)

        assert isinstance(item, ContributingEquipment)
        assert item.Manufacturer == dcm.Manufacturer


class TestLUT(TestCase):

    def setUp(self):
        super().setUp()
        self._lut_data = np.arange(10, 100, dtype=np.uint8)
        self._lut_data_16 = np.arange(510, 600, dtype=np.uint16)
        self._explanation = 'My LUT'

    def test_construction(self):
        first_value = 0
        lut = LUT(
            first_mapped_value=first_value,
            lut_data=self._lut_data,
        )
        assert lut.LUTDescriptor == [len(self._lut_data), first_value, 8]
        assert lut.bits_per_entry == 8
        assert lut.first_mapped_value == first_value
        assert np.array_equal(lut.lut_data, self._lut_data)
        assert not hasattr(lut, 'LUTExplanation')

        arr = np.array([0, 1, 0, 89, 1])
        expected = np.array([10, 11, 10, 99, 11])
        output = lut.apply(arr)
        assert output.dtype == np.uint8
        assert np.array_equal(output, expected)

        for dtype in [
            np.uint8,
            np.uint16,
            np.uint32,
            np.float32,
            np.float64,
            np.int16,
            np.int32,
            np.int64,
        ]:
            output = lut.apply(arr, dtype=dtype)
            assert output.dtype == dtype
            assert np.array_equal(output, expected.astype(dtype))

        for dtype in [
            np.int8,
        ]:
            with pytest.raises(TypeError):
                lut.apply(arr, dtype=dtype)

        for out_min, out_max in [
            (0.0, 1.0),
            (-10, -5),
            (100.0, 150.0),
        ]:
            for dtype in [
                np.float16,
                np.float32,
                np.float64,
            ]:
                scaled_data = lut.get_scaled_lut_data(
                    output_range=(out_min, out_max),
                    dtype=dtype,
                )
                assert scaled_data.min() == out_min
                assert scaled_data.max() == out_max
                assert scaled_data[0] == out_min
                assert scaled_data[-1] == out_max
                assert scaled_data.dtype == dtype

                scaled_data = lut.get_scaled_lut_data(
                    output_range=(out_min, out_max),
                    dtype=dtype,
                    invert=True,
                )
                assert scaled_data.min() == out_min
                assert scaled_data.max() == out_max
                assert scaled_data[-1] == out_min
                assert scaled_data[0] == out_max
                assert scaled_data.dtype == dtype

    def test_construction_16bit(self):
        first_value = 0
        lut = LUT(
            first_mapped_value=first_value,
            lut_data=self._lut_data_16
        )
        assert lut.LUTDescriptor == [len(self._lut_data), first_value, 16]
        assert lut.bits_per_entry == 16
        assert lut.first_mapped_value == first_value
        assert np.array_equal(lut.lut_data, self._lut_data_16)
        assert not hasattr(lut, 'LUTExplanation')

        arr = np.array([0, 1, 0, 89, 1])
        expected = np.array([510, 511, 510, 599, 511])
        output = lut.apply(arr)
        assert output.dtype == np.uint16
        assert np.array_equal(output, expected)

        for dtype in [
            np.uint16,
            np.uint32,
            np.float32,
            np.float64,
            np.int32,
            np.int64,
        ]:
            output = lut.apply(arr, dtype=dtype)
            assert output.dtype == dtype
            assert np.array_equal(output, expected.astype(dtype))

        for dtype in [
            np.uint8,
            np.int8,
            np.int16,
        ]:
            with pytest.raises(TypeError):
                lut.apply(arr, dtype=dtype)

        for out_min, out_max in [
            (0.0, 1.0),
            (-10, -5),
            (100.0, 150.0),
        ]:
            for dtype in [
                np.float32,
                np.float64,
            ]:
                scaled_data = lut.get_scaled_lut_data(
                    output_range=(out_min, out_max),
                    dtype=dtype,
                )
                assert scaled_data.min() == out_min
                assert scaled_data.max() == out_max
                assert scaled_data[0] == out_min
                assert scaled_data[-1] == out_max
                assert scaled_data.dtype == dtype

                scaled_data = lut.get_scaled_lut_data(
                    output_range=(out_min, out_max),
                    dtype=dtype,
                    invert=True,
                )
                assert scaled_data.min() == out_min
                assert scaled_data.max() == out_max
                assert scaled_data[-1] == out_min
                assert scaled_data[0] == out_max
                assert scaled_data.dtype == dtype

    def test_construction_explanation(self):
        first_value = 0
        lut = LUT(
            first_mapped_value=first_value,
            lut_data=self._lut_data_16,
            lut_explanation=self._explanation
        )
        assert lut.LUTDescriptor == [len(self._lut_data), first_value, 16]
        assert lut.bits_per_entry == 16
        assert lut.first_mapped_value == first_value
        assert np.array_equal(lut.lut_data, self._lut_data_16)
        assert lut.LUTExplanation == self._explanation


class TestModalityLUT(TestCase):

    def setUp(self):
        super().setUp()
        self._lut_data = np.arange(10, 100, dtype=np.uint8)
        self._lut_data_16 = np.arange(510, 600, dtype=np.uint16)
        self._explanation = 'My LUT'

    def test_construction(self):
        first_value = 0
        lut = ModalityLUT(
            lut_type=RescaleTypeValues.HU,
            first_mapped_value=first_value,
            lut_data=self._lut_data,
        )
        assert lut.ModalityLUTType == RescaleTypeValues.HU.value
        assert lut.LUTDescriptor == [len(self._lut_data), first_value, 8]
        assert lut.bits_per_entry == 8
        assert lut.first_mapped_value == first_value
        assert np.array_equal(lut.lut_data, self._lut_data)
        assert not hasattr(lut, 'LUTExplanation')

        arr = np.array([0, 1, 0, 89, 1])
        expected = np.array([10, 11, 10, 99, 11])
        output = lut.apply(arr)
        assert output.dtype == np.uint8
        assert np.array_equal(output, expected)

        for dtype in [
            np.uint16,
            np.uint32,
            np.int16,
            np.float16,
            np.float32,
            np.float64,
            np.int32,
            np.int64,
        ]:
            output = lut.apply(arr, dtype=dtype)
            assert output.dtype == dtype
            assert np.array_equal(output, expected.astype(dtype))

        for dtype in [
            np.int8,
        ]:
            with pytest.raises(TypeError):
                lut.apply(arr, dtype=dtype)

    def test_construction_16bit(self):
        first_value = 0
        lut = ModalityLUT(
            lut_type=RescaleTypeValues.HU,
            first_mapped_value=first_value,
            lut_data=self._lut_data_16
        )
        assert lut.ModalityLUTType == RescaleTypeValues.HU.value
        assert lut.LUTDescriptor == [len(self._lut_data_16), first_value, 16]
        assert lut.bits_per_entry == 16
        assert lut.first_mapped_value == first_value
        assert np.array_equal(lut.lut_data, self._lut_data_16)
        assert not hasattr(lut, 'LUTExplanation')

        arr = np.array([0, 1, 0, 89, 1])
        expected = np.array([510, 511, 510, 599, 511])
        output = lut.apply(arr)
        assert output.dtype == np.uint16
        assert np.array_equal(output, expected)

        for dtype in [
            np.uint16,
            np.uint32,
            np.float32,
            np.float64,
            np.int32,
            np.int64,
        ]:
            output = lut.apply(arr, dtype=dtype)
            assert output.dtype == dtype
            assert np.array_equal(output, expected.astype(dtype))

        for dtype in [
            np.uint8,
            np.int8,
            np.int16,
            np.float16,
        ]:
            with pytest.raises(TypeError):
                lut.apply(arr, dtype=dtype)

    def test_construction_string_type(self):
        first_value = 0
        lut_type = 'MY_MAPPING'
        lut = ModalityLUT(
            lut_type=lut_type,
            first_mapped_value=first_value,
            lut_data=self._lut_data_16
        )
        assert lut.ModalityLUTType == lut_type
        assert lut.LUTDescriptor == [len(self._lut_data_16), first_value, 16]
        assert np.array_equal(lut.lut_data, self._lut_data_16)
        assert not hasattr(lut, 'LUTExplanation')

    def test_construction_with_exp(self):
        first_value = 0
        lut = ModalityLUT(
            lut_type=RescaleTypeValues.HU,
            first_mapped_value=first_value,
            lut_data=self._lut_data_16,
            lut_explanation=self._explanation
        )
        assert lut.ModalityLUTType == RescaleTypeValues.HU.value
        assert lut.LUTDescriptor == [len(self._lut_data_16), first_value, 16]
        assert np.array_equal(lut.lut_data, self._lut_data_16)
        assert lut.LUTExplanation == self._explanation

    def test_construction_empty_data(self):
        with pytest.raises(ValueError):
            ModalityLUT(
                lut_type=RescaleTypeValues.HU,
                first_mapped_value=0,
                lut_data=np.array([]),  # empty data
            )

    def test_construction_negative_first_value(self):
        with pytest.raises(ValueError):
            ModalityLUT(
                lut_type=RescaleTypeValues.HU,
                first_mapped_value=-1,  # invalid
                lut_data=self._lut_data_16,
            )

    def test_construction_wrong_dtype(self):
        with pytest.raises(ValueError):
            ModalityLUT(
                lut_type=RescaleTypeValues.HU,
                first_mapped_value=0,
                lut_data=np.array([0, 1, 2], dtype=np.int16),  # invalid
            )


class TestModalityLUTTransformation(TestCase):

    def setUp(self):
        super().setUp()
        self._lut = ModalityLUT(
            lut_type=RescaleTypeValues.HU,
            first_mapped_value=0,
            lut_data=np.array([11, 22, 33, 44], np.uint8),
        )
        self._input_array = np.array(
            [
                [0, 1, 2, 3],
                [0, 1, 2, 3],
                [0, 1, 2, 3],
            ],
            dtype=np.uint8,
        )

    def test_with_lut(self):
        transf = ModalityLUTTransformation(modality_lut=self._lut)
        assert transf.has_lut()

        out = transf.apply(self._input_array)

        expected = np.array(
            [
                [11, 22, 33, 44],
                [11, 22, 33, 44],
                [11, 22, 33, 44],
            ]
        )

        assert np.array_equal(out, expected)
        assert out.dtype == np.uint8

    def test_with_scale_1(self):
        transf = ModalityLUTTransformation(
            rescale_type=RescaleTypeValues.HU,
            rescale_slope=1.0,
            rescale_intercept=0.0,
        )
        assert not transf.has_lut()

        out = transf.apply(self._input_array)

        expected = self._input_array

        assert np.array_equal(out, expected)
        assert out.dtype == np.float64

        for dtype in [
            np.uint8,
            np.uint16,
            np.uint32,
            np.uint64,
            np.float16,
            np.float32,
            np.float64,
            np.int16,
            np.int32,
            np.int64,
        ]:
            out = transf.apply(self._input_array, dtype=dtype)
            assert np.array_equal(out, expected)
            assert out.dtype == dtype

        for dtype in [np.int8]:
            msg = (
                f'Datatype {np.dtype(dtype)} does not have capacity for '
                'values with slope 1.00 and intercept 0.00.'
            )
            with pytest.raises(ValueError, match=msg):
                transf.apply(self._input_array, dtype=dtype)

        msg = (
            'An integer data type cannot be used if the input '
            'array is floating point.'
        )
        with pytest.raises(ValueError, match=msg):
            transf.apply(self._input_array.astype(np.float32), dtype=np.int64)

    def test_with_scale_2(self):
        transf = ModalityLUTTransformation(
            rescale_type=RescaleTypeValues.HU,
            rescale_slope=10.0,
            rescale_intercept=0.0,
        )
        assert not transf.has_lut()

        out = transf.apply(self._input_array)

        expected = self._input_array * 10

        assert np.array_equal(out, expected)
        assert out.dtype == np.float64

        for dtype in [
            np.uint16,
            np.uint32,
            np.uint64,
            np.float32,
            np.float64,
            np.int16,
            np.int32,
            np.int64,
        ]:
            out = transf.apply(self._input_array, dtype=dtype)
            assert np.array_equal(out, expected)
            assert out.dtype == dtype

        for dtype in [
            np.int8,
            np.uint8,
        ]:
            msg = (
                f'Datatype {np.dtype(dtype)} does not have capacity for '
                'values with slope 10.00 and intercept 0.00.'
            )
            with pytest.raises(ValueError, match=msg):
                transf.apply(self._input_array, dtype=dtype)

    def test_with_scale_3(self):
        transf = ModalityLUTTransformation(
            rescale_type=RescaleTypeValues.HU,
            rescale_slope=2.0,
            rescale_intercept=-1000.0,
        )
        assert not transf.has_lut()

        out = transf.apply(self._input_array)

        expected = self._input_array.astype(np.float64) * 2 - 1000

        assert np.array_equal(out, expected)
        assert out.dtype == np.float64

        for dtype in [
            np.float16,
            np.float32,
            np.float64,
            np.int16,
            np.int32,
            np.int64,
        ]:
            out = transf.apply(self._input_array, dtype=dtype)
            assert np.array_equal(out, expected)
            assert out.dtype == dtype

        for dtype in [
            np.uint8,
            np.uint16,
            np.uint32,
            np.uint64,
        ]:
            msg = (
                'An unsigned integer data type cannot be used if the '
                'intercept is negative.'
            )
            with pytest.raises(ValueError, match=msg):
                transf.apply(self._input_array, dtype=dtype)

        for dtype in [
            np.int8,
        ]:
            msg = (
                f'Datatype {np.dtype(dtype)} does not have capacity for '
                'values with slope 2.00 and intercept -1000.00.'
            )
            with pytest.raises(ValueError, match=msg):
                transf.apply(self._input_array, dtype=dtype)

    def test_with_scale_4(self):
        transf = ModalityLUTTransformation(
            rescale_type=RescaleTypeValues.HU,
            rescale_slope=3.14159,
            rescale_intercept=0.0,
        )
        assert not transf.has_lut()

        out = transf.apply(self._input_array)

        expected = self._input_array.astype(np.float64) * 3.14159
        assert np.array_equal(out, expected)
        assert out.dtype == np.float64

        for dtype in [
            np.float16,
            np.float32,
            np.float64,
        ]:
            expected = self._input_array.astype(np.float64) * dtype(3.14159)
            out = transf.apply(self._input_array, dtype=dtype)
            assert np.array_equal(out, expected)
            assert out.dtype == dtype

        for dtype in [
            np.int8,
            np.int16,
            np.int32,
            np.int64,
            np.uint8,
            np.uint16,
            np.uint32,
            np.uint64,
        ]:
            msg = (
                'An integer data type cannot be used if the slope '
                'or intercept is a non-integer value.'
            )
            with pytest.raises(ValueError, match=msg):
                transf.apply(self._input_array, dtype=dtype)


class TestPlanePositionSequence(TestCase):

    def test_construction_slide(self):
        coordinate_system = 'SLIDE'
        image_position = [0., 0., 0.]
        matrix_position = [0, 0]
        seq = PlanePositionSequence(
            coordinate_system=coordinate_system,
            image_position=image_position,
            pixel_matrix_position=matrix_position
        )
        assert len(seq) == 1
        item = seq[0]
        assert float(item.XOffsetInSlideCoordinateSystem) == image_position[0]
        assert float(item.YOffsetInSlideCoordinateSystem) == image_position[1]
        assert float(item.ZOffsetInSlideCoordinateSystem) == image_position[2]
        assert item.RowPositionInTotalImagePixelMatrix == matrix_position[1]
        assert item.ColumnPositionInTotalImagePixelMatrix == matrix_position[0]

    def test_construction_patient(self):
        coordinate_system = 'PATIENT'
        image_position = [0., 0., 0.]
        seq = PlanePositionSequence(
            coordinate_system=coordinate_system,
            image_position=image_position,
        )
        assert len(seq) == 1
        item = seq[0]
        assert item.ImagePositionPatient[0] == image_position[0]
        assert item.ImagePositionPatient[1] == image_position[1]
        assert item.ImagePositionPatient[2] == image_position[2]


class TestPlaneOrientationSequence(TestCase):

    def test_construction_slide(self):
        coordinate_system = 'SLIDE'
        image_orientation = [0., 1., 0., 1., 0., 0.]
        seq = PlaneOrientationSequence(
            coordinate_system=coordinate_system,
            image_orientation=image_orientation,
        )
        assert len(seq) == 1
        item = seq[0]
        assert item.ImageOrientationSlide[0] == image_orientation[0]
        assert item.ImageOrientationSlide[1] == image_orientation[1]
        assert item.ImageOrientationSlide[2] == image_orientation[2]
        assert item.ImageOrientationSlide[3] == image_orientation[3]
        assert item.ImageOrientationSlide[4] == image_orientation[4]
        assert item.ImageOrientationSlide[5] == image_orientation[5]

    def test_construction_patient(self):
        coordinate_system = 'PATIENT'
        image_orientation = [0., 1., 0., 1., 0., 0.]
        seq = PlaneOrientationSequence(
            coordinate_system=coordinate_system,
            image_orientation=image_orientation,
        )
        assert len(seq) == 1
        item = seq[0]
        assert item.ImageOrientationPatient[0] == image_orientation[0]
        assert item.ImageOrientationPatient[1] == image_orientation[1]
        assert item.ImageOrientationPatient[2] == image_orientation[2]
        assert item.ImageOrientationPatient[3] == image_orientation[3]
        assert item.ImageOrientationPatient[4] == image_orientation[4]
        assert item.ImageOrientationPatient[5] == image_orientation[5]


class TestPixelMeasuresSequence(TestCase):

    def test_construction(self):
        pixel_spacing = [0., 0.]
        slice_thickness = 0.
        seq = PixelMeasuresSequence(
            pixel_spacing=pixel_spacing,
            slice_thickness=slice_thickness
        )
        assert len(seq) == 1
        item = seq[0]
        assert item.PixelSpacing[0] == pixel_spacing[0]
        assert item.PixelSpacing[1] == pixel_spacing[1]
        assert item.SliceThickness == slice_thickness
        with pytest.raises(AttributeError):
            item.SpacingBetweenSlices  # noqa: B018

    def test_construction_with_spacing_between_slices(self):
        pixel_spacing = [0., 0.]
        slice_thickness = 0.
        spacing_between_slices = 0.
        seq = PixelMeasuresSequence(
            pixel_spacing=pixel_spacing,
            slice_thickness=slice_thickness,
            spacing_between_slices=spacing_between_slices
        )
        assert len(seq) == 1
        item = seq[0]
        assert item.SpacingBetweenSlices == spacing_between_slices


class TestSpecimenCollection(TestCase):

    def test_construction(self):
        procedure = codes.SCT.Biopsy
        seq = SpecimenCollection(procedure=procedure)
        assert len(seq) == 1
        assert not seq.is_root
        assert not seq.is_sr
        item = seq[0]
        assert item.name == codes.SCT.SpecimenCollection
        assert item.value == procedure
        assert item.relationship_type is None


class TestSpecimenSampling(TestCase):

    def test_construction(self):
        method = codes.SCT.BlockSectioning
        parent_id = '1'
        parent_type = codes.SCT.GrossSpecimen
        seq = SpecimenSampling(
            method=method,
            parent_specimen_id=parent_id,
            parent_specimen_type=parent_type
        )
        assert len(seq) == 3
        assert not seq.is_root
        assert not seq.is_sr
        method_item = seq[0]
        assert method_item.name == codes.DCM.SamplingMethod
        assert method_item.value == method
        assert method_item.relationship_type is None
        parent_id_item = seq[1]
        assert parent_id_item.name == codes.DCM.ParentSpecimenIdentifier
        assert parent_id_item.value == parent_id
        assert parent_id_item.relationship_type is None
        parent_type_item = seq[2]
        assert parent_type_item.name == codes.DCM.ParentSpecimenType
        assert parent_type_item.value == parent_type
        assert parent_type_item.relationship_type is None


class TestSpecimenStaining(TestCase):

    def test_construction(self):
        substances = [
            codes.SCT.HematoxylinStain,
            codes.SCT.WaterSolubleEosinStain
        ]
        seq = SpecimenStaining(substances=substances)
        assert len(seq) == 2
        assert not seq.is_root
        assert not seq.is_sr
        hematoxylin_item = seq[0]
        assert hematoxylin_item.name == codes.SCT.UsingSubstance
        assert hematoxylin_item.value == substances[0]
        assert hematoxylin_item.relationship_type is None
        eosin_item = seq[1]
        assert eosin_item.name == codes.SCT.UsingSubstance
        assert eosin_item.value == substances[1]
        assert eosin_item.relationship_type is None

    def test_construction_missing_substances(self):
        with pytest.raises(ValueError):
            SpecimenStaining(substances=[])


class TestSpecimenPreparationStep(TestCase):
    def test_construction_collection(self):
        specimen_id = 'specimen id'
        processing_type = codes.SCT.SpecimenCollection
        procedure = codes.SCT.Excision
        instance = SpecimenPreparationStep(
            specimen_id=specimen_id,
            processing_procedure=SpecimenCollection(procedure=procedure)
        )
        seq = instance.SpecimenPreparationStepContentItemSequence
        assert len(seq) == 3
        assert not seq.is_root
        assert not seq.is_sr
        assert instance.specimen_id == specimen_id
        specimen_id_item = seq[0]
        assert specimen_id_item.name == codes.DCM.SpecimenIdentifier
        assert specimen_id_item.value == specimen_id
        assert specimen_id_item.relationship_type is None

        assert instance.processing_type == processing_type
        processing_type_item = seq[1]
        assert processing_type_item.name == codes.DCM.ProcessingType
        assert processing_type_item.value == processing_type
        assert processing_type_item.relationship_type is None

        assert isinstance(instance.processing_procedure, SpecimenCollection)
        procedure_item = seq[2]
        assert procedure_item.name == codes.SCT.SpecimenCollection
        assert procedure_item.value == procedure
        assert procedure_item.relationship_type is None

    def test_construction_collection_from_dataset(self):
        specimen_id = 'specimen id'
        processing_type = codes.SCT.SpecimenCollection
        procedure = codes.SCT.Excision
        dataset = Dataset()
        dataset.SpecimenPreparationStepContentItemSequence = [
            TextContentItem(
                name=codes.DCM.SpecimenIdentifier,
                value=specimen_id
            ),
            CodeContentItem(
                name=codes.DCM.ProcessingType,
                value=processing_type
            ),
            CodeContentItem(
                name=codes.SCT.SpecimenCollection,
                value=procedure
            )
        ]
        dataset_reread = write_and_read_dataset(dataset)
        instance = SpecimenPreparationStep.from_dataset(dataset_reread)
        assert isinstance(instance, SpecimenPreparationStep)
        assert len(instance.SpecimenPreparationStepContentItemSequence) == 3
        assert instance.specimen_id == specimen_id
        assert instance.processing_type == processing_type
        assert instance.processing_procedure.procedure == procedure
        assert instance.fixative is None
        assert instance.embedding_medium is None
        processing_procedure = instance.processing_procedure
        assert isinstance(processing_procedure, SpecimenCollection)
        assert processing_procedure.procedure == procedure

    def test_construction_sampling(self):
        specimen_id = 'specimen id'
        processing_type = codes.SCT.SamplingOfTissueSpecimen
        method = codes.DCM.DissectionWithRepresentativeSectionsSubmission
        parent_specimen_id = 'parent specimen id'
        parent_specimen_type = codes.SCT.TissueSpecimen
        fixative = codes.SCT.Formalin
        embedding_medium = codes.SCT.ParaffinWax
        instance = SpecimenPreparationStep(
            specimen_id=specimen_id,
            processing_procedure=SpecimenSampling(
                method=method,
                parent_specimen_id=parent_specimen_id,
                parent_specimen_type=parent_specimen_type
            ),
            fixative=fixative,
            embedding_medium=embedding_medium
        )
        seq = instance.SpecimenPreparationStepContentItemSequence
        assert len(seq) == 7
        assert not seq.is_root
        assert not seq.is_sr

        assert instance.specimen_id == specimen_id
        assert instance.processing_type == processing_type
        assert instance.fixative == fixative
        assert instance.embedding_medium == embedding_medium
        assert isinstance(instance.processing_procedure, SpecimenSampling)

        specimen_id_item = seq[0]
        assert specimen_id_item.name == codes.DCM.SpecimenIdentifier
        assert specimen_id_item.value == specimen_id
        assert specimen_id_item.relationship_type is None

        processing_type_item = seq[1]
        assert processing_type_item.name == codes.DCM.ProcessingType
        assert processing_type_item.value == processing_type
        assert processing_type_item.relationship_type is None

        method_item = seq[2]
        assert method_item.name == codes.DCM.SamplingMethod
        assert method_item.value == method
        assert method_item.relationship_type is None

        parent_specimen_id_item = seq[3]
        assert parent_specimen_id_item.name == codes.DCM.ParentSpecimenIdentifier  # noqa: E501
        assert parent_specimen_id_item.value == parent_specimen_id
        assert parent_specimen_id_item.relationship_type is None

        parent_specimen_type_item = seq[4]
        assert parent_specimen_type_item.name == codes.DCM.ParentSpecimenType
        assert parent_specimen_type_item.value == parent_specimen_type
        assert parent_specimen_type_item.relationship_type is None

        fixative_item = seq[5]
        assert fixative_item.name == codes.SCT.TissueFixative
        assert fixative_item.value == fixative
        assert fixative_item.relationship_type is None

        embedding_medium_item = seq[6]
        assert embedding_medium_item.name == codes.SCT.TissueEmbeddingMedium
        assert embedding_medium_item.value == embedding_medium
        assert embedding_medium_item.relationship_type is None

    def test_construction_sampling_from_dataset(self):
        specimen_id = 'specimen id'
        processing_type = codes.SCT.SamplingOfTissueSpecimen
        method = codes.DCM.DissectionWithRepresentativeSectionsSubmission
        parent_specimen_id = 'parent specimen id'
        parent_specimen_type = codes.SCT.TissueSpecimen
        fixative = codes.SCT.Formalin
        embedding_medium = codes.SCT.ParaffinWax
        dataset = Dataset()
        dataset.SpecimenPreparationStepContentItemSequence = [
            TextContentItem(
                name=codes.DCM.SpecimenIdentifier,
                value=specimen_id
            ),
            CodeContentItem(
                name=codes.DCM.ProcessingType,
                value=processing_type
            ),
            CodeContentItem(
                name=codes.DCM.SamplingMethod,
                value=method
            ),
            TextContentItem(
                name=codes.DCM.ParentSpecimenIdentifier,
                value=parent_specimen_id
            ),
            CodeContentItem(
                name=codes.DCM.ParentSpecimenType,
                value=parent_specimen_type
            ),
            CodeContentItem(
                name=codes.SCT.TissueFixative,
                value=fixative
            ),
            CodeContentItem(
                name=codes.SCT.TissueEmbeddingMedium,
                value=embedding_medium
            )
        ]
        dataset_reread = write_and_read_dataset(dataset)
        instance = SpecimenPreparationStep.from_dataset(dataset_reread)
        assert isinstance(instance, SpecimenPreparationStep)
        assert instance.specimen_id == specimen_id
        assert instance.processing_type == processing_type
        assert instance.fixative == fixative
        assert instance.embedding_medium == embedding_medium
        processing_procedure = instance.processing_procedure
        assert isinstance(processing_procedure, SpecimenSampling)
        assert processing_procedure.method == method
        assert processing_procedure.parent_specimen_id == parent_specimen_id
        assert processing_procedure.parent_specimen_type == parent_specimen_type

    def test_construction_staining(self):
        specimen_id = 'specimen id'
        processing_type = codes.SCT.Staining
        substance = codes.SCT.HematoxylinStain
        instance = SpecimenPreparationStep(
            specimen_id=specimen_id,
            processing_procedure=SpecimenStaining(substances=[substance])
        )
        seq = instance.SpecimenPreparationStepContentItemSequence
        assert len(seq) == 3
        assert not seq.is_root
        assert not seq.is_sr

        assert instance.specimen_id == specimen_id
        assert instance.processing_type == processing_type
        assert instance.fixative is None
        assert instance.embedding_medium is None

        specimen_id_item = seq[0]
        assert specimen_id_item.name == codes.DCM.SpecimenIdentifier
        assert specimen_id_item.value == specimen_id
        assert specimen_id_item.relationship_type is None

        processing_type_item = seq[1]
        assert processing_type_item.name == codes.DCM.ProcessingType
        assert processing_type_item.value == processing_type
        assert processing_type_item.relationship_type is None

        staining_item = seq[2]
        assert staining_item.name == codes.SCT.UsingSubstance
        assert staining_item.value == substance
        assert staining_item.relationship_type is None

    def test_construction_staining_from_dataset(self):
        specimen_id = 'specimen id'
        processing_type = codes.SCT.Staining
        substance = codes.SCT.HematoxylinStain
        dataset = Dataset()
        dataset.SpecimenPreparationStepContentItemSequence = [
            TextContentItem(
                name=codes.DCM.SpecimenIdentifier,
                value=specimen_id
            ),
            CodeContentItem(
                name=codes.DCM.ProcessingType,
                value=processing_type
            ),
            CodeContentItem(
                name=codes.SCT.UsingSubstance,
                value=substance
            ),
        ]
        dataset_reread = write_and_read_dataset(dataset)
        instance = SpecimenPreparationStep.from_dataset(dataset_reread)
        assert isinstance(instance, SpecimenPreparationStep)
        assert instance.specimen_id == specimen_id
        assert instance.processing_type == processing_type
        assert instance.fixative is None
        assert instance.embedding_medium is None
        processing_procedure = instance.processing_procedure
        assert isinstance(processing_procedure, SpecimenStaining)
        assert processing_procedure.substances == [substance]

    def test_construction_processing(self):
        specimen_id = 'specimen id'
        processing_type = codes.SCT.SpecimenProcessing
        description = codes.SCT.SpecimenFreezing
        instance = SpecimenPreparationStep(
            specimen_id=specimen_id,
            processing_procedure=SpecimenProcessing(description=description),
        )
        seq = instance.SpecimenPreparationStepContentItemSequence
        assert len(seq) == 3
        assert not seq.is_root
        assert not seq.is_sr

        assert instance.specimen_id == specimen_id
        assert instance.processing_type == processing_type
        assert instance.processing_datetime is None
        assert instance.issuer_of_specimen_id is None
        assert instance.fixative is None
        assert instance.embedding_medium is None

        specimen_id_item = seq[0]
        assert specimen_id_item.name == codes.DCM.SpecimenIdentifier
        assert specimen_id_item.value == specimen_id
        assert specimen_id_item.relationship_type is None

        processing_type_item = seq[1]
        assert processing_type_item.name == codes.DCM.ProcessingType
        assert processing_type_item.value == processing_type
        assert processing_type_item.relationship_type is None

        processing_step_description_item = seq[2]
        assert (
            processing_step_description_item.name ==
            codes.DCM.ProcessingStepDescription
        )
        assert processing_step_description_item.value == description
        assert processing_step_description_item.relationship_type is None

    def test_construction_processing_optionals(self):
        specimen_id = 'specimen id'
        processing_type = codes.SCT.SpecimenCollection
        procedure = codes.SCT.Excision
        processing_procedure = SpecimenCollection(procedure=procedure)
        processing_datetime = datetime.datetime(2023, 6, 17, 21, 38, 14)
        processing_description = 'processing description'
        issuer_of_specimen_id = IssuerOfIdentifier("issuer id")
        fixative = CodedConcept("fixative", "test", "test fixative")
        embedding_medium = CodedConcept("embedding", "test", "test embedding")
        specimen_container = CodedConcept(
            "specimen container",
            "test",
            "test specimen container"
        )
        specimen_type = CodedConcept(
            "specimen type",
            "test",
            "test specimen type"
        )

        instance = SpecimenPreparationStep(
            specimen_id=specimen_id,
            processing_procedure=processing_procedure,
            processing_description=processing_description,
            processing_datetime=processing_datetime,
            issuer_of_specimen_id=issuer_of_specimen_id,
            fixative=fixative,
            embedding_medium=embedding_medium,
            specimen_container=specimen_container,
            specimen_type=specimen_type
        )

        seq = instance.SpecimenPreparationStepContentItemSequence
        assert len(seq) == 10

        specimen_id_item = seq[0]
        assert specimen_id_item.name == codes.DCM.SpecimenIdentifier
        assert specimen_id_item.value == specimen_id
        assert specimen_id_item.relationship_type is None

        issuer_of_specimen_id_item = seq[1]
        assert (
            issuer_of_specimen_id_item.name ==
            codes.DCM.IssuerOfSpecimenIdentifier
        )
        assert (
            issuer_of_specimen_id_item.value ==
            issuer_of_specimen_id.LocalNamespaceEntityID
        )
        assert issuer_of_specimen_id_item.relationship_type is None

        processing_type_item = seq[2]
        assert (
            processing_type_item.name == codes.DCM.ProcessingType
        )
        assert processing_type_item.value == processing_type
        assert processing_type_item.relationship_type is None

        processing_datetime_item = seq[3]
        assert (
            processing_datetime_item.name == codes.DCM.DatetimeOfProcessing
        )
        assert processing_datetime_item.value == processing_datetime
        assert processing_datetime_item.relationship_type is None

        processing_description_item = seq[4]
        assert (
            processing_description_item.name ==
            codes.DCM.ProcessingStepDescription
        )
        assert processing_description_item.value == processing_description
        assert processing_description_item.relationship_type is None

        collection_step_item = seq[5]
        assert (
            collection_step_item.name == codes.SCT.SpecimenCollection
        )
        assert collection_step_item.value == procedure
        assert collection_step_item.relationship_type is None

        fixative_item = seq[6]
        assert fixative_item.name == codes.SCT.TissueFixative
        assert fixative_item.value == fixative
        assert fixative_item.relationship_type is None

        embedding_item = seq[7]
        assert embedding_item.name == codes.SCT.TissueEmbeddingMedium
        assert embedding_item.value == embedding_medium
        assert embedding_item.relationship_type is None

        specimen_container_item = seq[8]
        assert specimen_container_item.name == codes.SCT.SpecimenContainer
        assert specimen_container_item.value == specimen_container
        assert specimen_container_item.relationship_type is None

        specimen_type_item = seq[9]
        assert specimen_type_item.name == codes.SCT.SpecimenType
        assert specimen_type_item.value == specimen_type
        assert specimen_type_item.relationship_type is None

    def test_construction_processing_from_dataset(self):
        specimen_id = 'specimen id'
        processing_type = codes.SCT.SpecimenProcessing
        description = codes.SCT.SpecimenFreezing
        dataset = Dataset()
        dataset.SpecimenPreparationStepContentItemSequence = [
            TextContentItem(
                name=codes.DCM.SpecimenIdentifier,
                value=specimen_id
            ),
            CodeContentItem(
                name=codes.DCM.ProcessingType,
                value=processing_type
            ),
            CodeContentItem(
                name=codes.DCM.ProcessingStepDescription,
                value=description
            ),
        ]
        dataset_reread = write_and_read_dataset(dataset)
        instance = SpecimenPreparationStep.from_dataset(dataset_reread)
        assert isinstance(instance, SpecimenPreparationStep)
        assert instance.specimen_id == specimen_id
        assert instance.processing_type == processing_type
        assert instance.fixative is None
        assert instance.embedding_medium is None
        processing_procedure = instance.processing_procedure
        assert isinstance(processing_procedure, SpecimenProcessing)
        assert processing_procedure.description == description

    def test_construction_processing_from_dataset_optionals(self):
        specimen_id = 'specimen id'
        processing_type = codes.SCT.SpecimenCollection
        procedure = codes.SCT.Excision
        processing_procedure = SpecimenCollection(procedure=procedure)
        processing_description = "processing description"
        processing_datetime = datetime.datetime(2023, 6, 17, 21, 38, 14)
        issuer_of_specimen_id = IssuerOfIdentifier("issuer id")
        fixative = CodedConcept("fixative", "test", "test fixative")
        embedding_medium = CodedConcept("embedding", "test", "test embedding")
        specimen_container = CodedConcept(
            "specimen container",
            "test",
            "test specimen container"
        )
        specimen_type = CodedConcept(
            "specimen type",
            "test",
            "test specimen type"
        )
        dataset = Dataset()
        dataset.SpecimenPreparationStepContentItemSequence = [
            TextContentItem(
                name=codes.DCM.SpecimenIdentifier,
                value=specimen_id
            ),
            TextContentItem(
                name=codes.DCM.IssuerOfSpecimenIdentifier,
                value=issuer_of_specimen_id.LocalNamespaceEntityID
            ),
            DateTimeContentItem(
                name=codes.DCM.DatetimeOfProcessing,
                value=processing_datetime
            ),
            CodeContentItem(
                name=codes.DCM.ProcessingType,
                value=processing_type
            ),
            TextContentItem(
                name=codes.DCM.ProcessingStepDescription,
                value=processing_description
            ),
            CodeContentItem(
                name=codes.SCT.SpecimenCollection,
                value=procedure
            ),
            CodeContentItem(
                name=codes.SCT.TissueFixative,
                value=fixative
            ),
            CodeContentItem(
                name=codes.SCT.TissueEmbeddingMedium,
                value=embedding_medium
            ),
            CodeContentItem(
                name=codes.SCT.SpecimenContainer,
                value=specimen_container
            ),
            CodeContentItem(
                name=codes.SCT.SpecimenType,
                value=specimen_type
            )
        ]
        dataset_reread = write_and_read_dataset(dataset)
        instance = SpecimenPreparationStep.from_dataset(dataset_reread)
        assert isinstance(instance, SpecimenPreparationStep)
        assert instance.specimen_id == specimen_id
        assert instance.processing_type == processing_type
        assert instance.fixative == fixative
        assert instance.embedding_medium == embedding_medium
        assert instance.processing_description == processing_description
        processing_procedure = instance.processing_procedure
        assert isinstance(processing_procedure, SpecimenCollection)
        assert processing_procedure.procedure == procedure
        assert instance.processing_datetime == processing_datetime
        assert isinstance(instance.issuer_of_specimen_id, str)
        assert (
            instance.issuer_of_specimen_id ==
            issuer_of_specimen_id.LocalNamespaceEntityID
        )
        assert instance.specimen_container == specimen_container
        assert instance.specimen_type == specimen_type


class TestVOILUTTransformation(TestCase):

    def setUp(self):
        super().setUp()
        self._lut = VOILUT(
            first_mapped_value=0,
            lut_data=np.array([10, 11, 12], np.uint16)
        )

    def test_construction_basic(self):
        lut = VOILUTTransformation(
            window_center=40.0,
            window_width=400.0
        )
        assert lut.WindowCenter == 40.0
        assert lut.WindowWidth == 400.0
        assert not hasattr(lut, 'VOILUTSequence')
        assert not lut.has_lut()

        input_array = np.array(
            [
                [-200, -200, -200],
                [-160, -160, -160],
                [39.5, 39.5, 39.5],
                [239, 239, 239],
                [300, 300, 300],
            ]
        )

        expected = np.array(
            [
                [0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0],
                [0.5, 0.5, 0.5],
                [1.0, 1.0, 1.0],
                [1.0, 1.0, 1.0],
            ]
        )
        inverted_expected = np.flipud(expected)

        out = lut.apply(array=input_array)
        assert np.array_equal(expected, out)
        assert out.dtype == np.float64

        # Check with a different dtype
        for dtype in [np.float16, np.float32, np.float64]:
            out = lut.apply(array=input_array, dtype=dtype)
            assert np.allclose(expected, out)
            assert out.dtype == dtype

            out = lut.apply(array=input_array, dtype=dtype, invert=True)
            assert np.allclose(inverted_expected, out)
            assert out.dtype == dtype

        for dtype in [np.int16, np.uint8, np.int64]:
            msg = f'Data type "{np.dtype(dtype)}" is not suitable.'
            with pytest.raises(ValueError, match=msg):
                lut.apply(array=input_array, dtype=dtype)

        # Check with a different window
        expected = np.array(
            [
                [-0.5, -0.5, -0.5],
                [-0.5, -0.5, -0.5],
                [0.0, 0.0, 0.0],
                [0.5, 0.5, 0.5],
                [0.5, 0.5, 0.5],
            ]
        )
        out = lut.apply(
            array=input_array,
            output_range=(-0.5, 0.5),
        )
        assert np.array_equal(expected, out)
        assert out.dtype == np.float64

    def test_construction_explanation(self):
        lut = VOILUTTransformation(
            window_center=40.0,
            window_width=400.0,
            window_explanation='Soft Tissue Window'
        )
        assert lut.WindowCenter == 40.0
        assert lut.WindowWidth == 400.0
        assert not lut.has_lut()

    def test_construction_multiple(self):
        lut = VOILUTTransformation(
            window_center=[600.0, 40.0],
            window_width=[1500.0, 400.0],
            window_explanation=['Lung Window', 'Soft Tissue Window'],
        )
        assert lut.WindowCenter == [600.0, 40.0]
        assert lut.WindowWidth == [1500.0, 400.0]
        assert not lut.has_lut()

        input_array_lung = np.array(
            [
                [-200, -200, -200],
                [-150, -150, -150],
                [599.5, 599.5, 599.5],
                [1350, 1350, 1350],
                [1400, 1400, 1400],
            ]
        )

        input_array_soft_tissue = np.array(
            [
                [-200, -200, -200],
                [-160, -160, -160],
                [39.5, 39.5, 39.5],
                [239, 239, 239],
                [300, 300, 300],
            ]
        )

        expected = np.array(
            [
                [0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0],
                [0.5, 0.5, 0.5],
                [1.0, 1.0, 1.0],
                [1.0, 1.0, 1.0],
            ]
        )

        out = lut.apply(array=input_array_lung, voi_transform_selector=0)
        assert np.allclose(expected, out)
        assert out.dtype == np.float64

        out = lut.apply(
            array=input_array_soft_tissue,
            voi_transform_selector=1
        )
        assert np.array_equal(expected, out)
        assert out.dtype == np.float64

        out = lut.apply(
            array=input_array_soft_tissue,
            voi_transform_selector=-1
        )
        assert np.array_equal(expected, out)
        assert out.dtype == np.float64

    def test_construction_multiple_mismatch1(self):
        with pytest.raises(ValueError):
            VOILUTTransformation(
                window_center=40.0,
                window_width=[400.0, 1500.0],
            )

    def test_construction_multiple_mismatch2(self):
        with pytest.raises(TypeError):
            VOILUTTransformation(
                window_center=[40.0, 600.0],
                window_width=400.0,
            )

    def test_construction_multiple_mismatch3(self):
        with pytest.raises(ValueError):
            VOILUTTransformation(
                window_center=[40.0, 600.0],
                window_width=[400.0, 1500.0, -50.0],
            )

    def test_construction_explanation_mismatch(self):
        with pytest.raises(TypeError):
            VOILUTTransformation(
                window_center=[40.0, 600.0],
                window_width=[400.0, 1500.0],
                window_explanation='Lung Window',
            )

    def test_construction_explanation_mismatch2(self):
        with pytest.raises(ValueError):
            VOILUTTransformation(
                window_center=40.0,
                window_width=400.0,
                window_explanation=['Soft Tissue Window', 'Lung Window'],
            )

    def test_construction_sigmoid(self):
        window_center = 40.0
        window_width = 400.0
        voi_lut_function = VOILUTFunctionValues.SIGMOID
        lut = VOILUTTransformation(
            window_center=window_center,
            window_width=window_width,
            voi_lut_function=voi_lut_function,
        )
        assert lut.WindowCenter == 40.0
        assert lut.WindowWidth == 400.0
        assert lut.VOILUTFunction == voi_lut_function.value
        assert not lut.has_lut()

        input_array = np.array(
            [
                [-2000, -20000, -2000],
                [40, 40, 40],
                [3000, 3000, 3000],
            ]
        )

        expected = np.array(
            [
                [0.0, 0.0, 0.0],
                [0.5, 0.5, 0.5],
                [1.0, 1.0, 1.0],
            ]
        )

        out = lut.apply(array=input_array)
        assert np.allclose(expected, out)
        assert out.dtype == np.float64

        # Check with a different dtype
        for dtype in [np.float16, np.float32, np.float64]:
            out = lut.apply(array=input_array, dtype=dtype)
            assert np.allclose(expected, out)
            assert out.dtype == dtype

        expected = np.array(
            [
                [10.0, 10.0, 10.0],
                [15.0, 15.0, 15.0],
                [20.0, 20.0, 20.0],
            ]
        )

        out = lut.apply(
            array=input_array,
            output_range=(10.0, 20.0),
        )
        assert np.allclose(expected, out)
        assert out.dtype == np.float64

        # test with invert
        inverted_expected = np.flipud(expected)
        out = lut.apply(
            array=input_array,
            output_range=(10.0, 20.0),
            invert=True,
        )
        assert np.allclose(inverted_expected, out)
        assert out.dtype == np.float64

    def test_construction_linear_exact(self):
        window_center = 40.0
        window_width = 400.0
        voi_lut_function = VOILUTFunctionValues.LINEAR_EXACT
        lut = VOILUTTransformation(
            window_center=window_center,
            window_width=window_width,
            voi_lut_function=voi_lut_function,
        )
        assert lut.WindowCenter == 40.0
        assert lut.WindowWidth == 400.0
        assert lut.VOILUTFunction == voi_lut_function.value
        assert not lut.has_lut()

        input_array = np.array(
            [
                [-200, -200, -200],
                [-160, -160, -160],
                [40, 40, 40],
                [240, 240, 240],
                [300, 300, 300],
            ],
            np.int16
        )

        expected = np.array(
            [
                [0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0],
                [0.5, 0.5, 0.5],
                [1.0, 1.0, 1.0],
                [1.0, 1.0, 1.0],
            ]
        )

        out = lut.apply(array=input_array)
        assert np.array_equal(expected, out)
        assert out.dtype == np.float64

        # Check with a different window
        expected = np.array(
            [
                [-20.0, -20.0, -20.0],
                [-20.0, -20.0, -20.0],
                [-15.0, -15.0, -15.0],
                [-10.0, -10.0, -10.0],
                [-10.0, -10.0, -10.0],
            ]
        )
        out = lut.apply(
            array=input_array,
            output_range=(-20.0, -10.0),
        )
        assert np.array_equal(expected, out)
        assert out.dtype == np.float64

        # Check inverted
        expected = np.array(
            [
                [-10.0, -10.0, -10.0],
                [-10.0, -10.0, -10.0],
                [-15.0, -15.0, -15.0],
                [-20.0, -20.0, -20.0],
                [-20.0, -20.0, -20.0],
            ]
        )
        out = lut.apply(
            array=input_array,
            output_range=(-20.0, -10.0),
            invert=True,
            dtype=np.float32
        )
        assert np.array_equal(expected, out)
        assert out.dtype == np.float32

    def test_construction_luts(self):
        lut = VOILUTTransformation(voi_luts=[self._lut])
        assert len(lut.VOILUTSequence) == 1
        assert not hasattr(lut, 'WindowWidth')
        assert not hasattr(lut, 'WindowCenter')
        assert lut.has_lut()

        input_array = np.array(
            [
                [0, 0, 0],
                [1, 1, 1],
                [2, 2, 2],
            ],
            dtype=np.uint8
        )

        expected = np.array(
            [
                [0.0, 0.0, 0.0],
                [0.5, 0.5, 0.5],
                [1.0, 1.0, 1.0],
            ],
        )
        out = lut.apply(input_array)
        assert np.array_equal(expected, out)

        expected = np.array(
            [
                [1.0, 1.0, 1.0],
                [0.5, 0.5, 0.5],
                [0.0, 0.0, 0.0],
            ],
        )
        out = lut.apply(input_array, invert=True)
        assert np.array_equal(expected, out)

        expected = np.array(
            [
                [1.0, 1.0, 1.0],
                [3.5, 3.5, 3.5],
                [6.0, 6.0, 6.0],
            ],
        )
        out = lut.apply(input_array, output_range=(1.0, 6.0))
        assert np.array_equal(expected, out)

        expected = np.array(
            [
                [6.0, 6.0, 6.0],
                [3.5, 3.5, 3.5],
                [1.0, 1.0, 1.0],
            ],
        )
        out = lut.apply(input_array, output_range=(1.0, 6.0), invert=True)
        assert np.array_equal(expected, out)

    def test_construction_both(self):
        lut = VOILUTTransformation(
            window_center=40.0,
            window_width=400.0,
            voi_luts=[self._lut]
        )
        assert len(lut.VOILUTSequence) == 1
        assert lut.WindowCenter == 40.0
        assert lut.WindowWidth == 400.0
        assert lut.has_lut()

    def test_construction_neither(self):
        with pytest.raises(TypeError):
            VOILUTTransformation()


class TestReferencedImageSequence(TestCase):

    def setUp(self):
        super().setUp()
        self._ct_series = [
            dcmread(f)
            for f in get_testdata_files('dicomdirtests/77654033/CT2/*')
        ]
        self._ct_multiframe = dcmread(get_testdata_file('eCT_Supplemental.dcm'))
        self._seg = dcmread(
            'data/test_files/seg_image_ct_binary_overlap.dcm'
        )

    def test_construction_ref_ims(self):
        ref_ims = ReferencedImageSequence(
            referenced_images=self._ct_series
        )
        assert len(ref_ims) == len(self._ct_series)

    def test_construction_empty(self):
        with pytest.raises(ValueError):
            ReferencedImageSequence(
                referenced_images=[]
            )

    def test_construction_frame_number(self):
        ref_ims = ReferencedImageSequence(
            referenced_images=[self._ct_multiframe],
            referenced_frame_number=1
        )
        assert len(ref_ims) == 1
        assert ref_ims[0].ReferencedFrameNumber == 1

    def test_construction_multi_frame_numbers(self):
        ref_ims = ReferencedImageSequence(
            referenced_images=[self._ct_multiframe],
            referenced_frame_number=[1, 2]
        )
        assert len(ref_ims) == 1
        assert ref_ims[0].ReferencedFrameNumber == [1, 2]

    def test_construction_invalid_frame_number_1(self):
        with pytest.raises(ValueError):
            ReferencedImageSequence(
                referenced_images=[self._ct_multiframe],
                referenced_frame_number=0
            )

    def test_construction_invalid_frame_number_2(self):
        with pytest.raises(ValueError):
            ReferencedImageSequence(
                referenced_images=[self._ct_multiframe],
                referenced_frame_number=self._ct_multiframe.NumberOfFrames + 1
            )

    def test_construction_invalid_frame_number_3(self):
        nonexistent_frame = self._ct_multiframe.NumberOfFrames + 1
        with pytest.raises(ValueError):
            ReferencedImageSequence(
                referenced_images=[self._ct_multiframe],
                referenced_frame_number=[1, nonexistent_frame]
            )

    def test_construction_frame_number_single_frames(self):
        with pytest.raises(ValueError):
            ReferencedImageSequence(
                referenced_images=self._ct_series,
                referenced_frame_number=0
            )

    def test_construction_segment_number(self):
        ref_ims = ReferencedImageSequence(
            referenced_images=[self._seg],
            referenced_segment_number=1
        )
        assert len(ref_ims) == 1
        assert ref_ims[0].ReferencedSegmentNumber == 1

    def test_construction_segment_number_non_seg(self):
        with pytest.raises(ValueError):
            ReferencedImageSequence(
                referenced_images=self._ct_series,
                referenced_segment_number=1
            )

    def test_construction_segment_number_multiple(self):
        ref_ims = ReferencedImageSequence(
            referenced_images=[self._seg],
            referenced_segment_number=[1, 2]
        )
        assert len(ref_ims) == 1
        assert ref_ims[0].ReferencedSegmentNumber == [1, 2]

    def test_construction_segment_number_and_frames(self):
        ref_ims = ReferencedImageSequence(
            referenced_images=[self._seg],
            referenced_segment_number=1,
            referenced_frame_number=[1, 2, 3],
        )
        assert len(ref_ims) == 1
        assert ref_ims[0].ReferencedSegmentNumber == 1
        assert ref_ims[0].ReferencedFrameNumber == [1, 2, 3]

    def test_construction_segment_number_and_frames_mismatch(self):
        with pytest.raises(ValueError):
            ReferencedImageSequence(
                referenced_images=[self._seg],
                referenced_segment_number=2,
                referenced_frame_number=[1, 2, 3],  # segment frame mismatch
            )

    def test_construction_invalid_segment_number_1(self):
        with pytest.raises(ValueError):
            ReferencedImageSequence(
                referenced_images=[self._seg],
                referenced_segment_number=0
            )

    def test_construction_invalid_segment_number_2(self):
        invalid_segment_number = len(self._seg.SegmentSequence) + 1
        with pytest.raises(ValueError):
            ReferencedImageSequence(
                referenced_images=[self._seg],
                referenced_segment_number=invalid_segment_number
            )

    def test_construction_invalid_segment_number_3(self):
        invalid_segment_number = len(self._seg.SegmentSequence) + 1
        with pytest.raises(ValueError):
            ReferencedImageSequence(
                referenced_images=[self._seg],
                referenced_segment_number=[1, invalid_segment_number]
            )

    def test_construction_duplicate(self):
        with pytest.raises(ValueError):
            ReferencedImageSequence(
                referenced_images=self._ct_series * 2,
            )


class TestPaletteColorLUT(TestCase):

    def test_construction_16bit(self):
        lut_data = np.arange(10, 120, dtype=np.uint16)
        first_mapped_value = 32
        lut = PaletteColorLUT(first_mapped_value, lut_data, color='red')

        assert len(lut.RedPaletteColorLookupTableDescriptor) == 3
        assert lut.RedPaletteColorLookupTableDescriptor[0] == 110
        assert lut.RedPaletteColorLookupTableDescriptor[1] == 32
        assert lut.RedPaletteColorLookupTableDescriptor[2] == 16
        assert not hasattr(lut, 'BluePaletteColorLookupTableDescriptor')
        assert not hasattr(lut, 'GreenPaletteColorLookupTableDescriptor')
        assert len(lut.RedPaletteColorLookupTableData) == lut_data.shape[0] * 2
        assert not hasattr(lut, 'BluePaletteColorLookupTableData')
        assert not hasattr(lut, 'GreenPaletteColorLookupTableData')

        assert lut.number_of_entries == lut_data.shape[0]
        assert lut.first_mapped_value == first_mapped_value
        assert lut.bits_per_entry == 16
        assert lut.lut_data.dtype == np.uint16
        np.array_equal(lut.lut_data, lut_data)

        arr = np.array([32, 33, 32, 132])
        expected = np.array([10, 11, 10, 110])
        output = lut.apply(arr)
        assert output.dtype == np.uint16
        assert np.array_equal(output, expected)

        for dtype in [
            np.uint16,
            np.uint32,
            np.float32,
            np.float64,
            np.int32,
            np.int64,
        ]:
            output = lut.apply(arr, dtype=dtype)
            assert output.dtype == dtype
            assert np.array_equal(output, expected.astype(dtype))

        for dtype in [
            np.uint8,
            np.int8,
            np.int16,
        ]:
            with pytest.raises(TypeError):
                lut.apply(arr, dtype=dtype)

    def test_construction_8bit(self):
        lut_data = np.arange(0, 256, dtype=np.uint8)
        first_mapped_value = 0
        lut = PaletteColorLUT(first_mapped_value, lut_data, color='blue')

        assert len(lut.BluePaletteColorLookupTableDescriptor) == 3
        assert lut.BluePaletteColorLookupTableDescriptor[0] == 256
        assert lut.BluePaletteColorLookupTableDescriptor[1] == 0
        assert lut.BluePaletteColorLookupTableDescriptor[2] == 8
        assert not hasattr(lut, 'RedPaletteColorLookupTableDescriptor')
        assert not hasattr(lut, 'GreenPaletteColorLookupTableDescriptor')
        expected_len = lut_data.shape[0]
        assert len(lut.BluePaletteColorLookupTableData) == expected_len
        assert not hasattr(lut, 'RedPaletteColorLookupTableData')
        assert not hasattr(lut, 'GreenPaletteColorLookupTableData')

        assert lut.number_of_entries == lut_data.shape[0]
        assert lut.first_mapped_value == first_mapped_value
        assert lut.bits_per_entry == 8
        assert lut.lut_data.dtype == np.uint8
        np.array_equal(lut.lut_data, lut_data)

        arr = np.array([0, 1, 0, 255])
        expected = np.array([0, 1, 0, 255])
        output = lut.apply(arr)
        assert output.dtype == np.uint8
        assert np.array_equal(output, expected)

        for dtype in [
            np.uint16,
            np.uint32,
            np.int16,
            np.float32,
            np.float64,
            np.int32,
            np.int64,
        ]:
            output = lut.apply(arr, dtype=dtype)
            assert output.dtype == dtype
            assert np.array_equal(output, expected.astype(dtype))

        for dtype in [
            np.int8,
        ]:
            with pytest.raises(TypeError):
                lut.apply(arr, dtype=dtype)


class TestPaletteColorLUTTransformation(TestCase):

    def setUp(self):
        super().setUp()

    def test_construction(self):
        for bits, dtype in [(8, np.uint8), (16, np.uint16)]:
            r_lut_data = np.arange(10, 120, dtype=dtype)
            g_lut_data = np.arange(20, 130, dtype=dtype)
            b_lut_data = np.arange(30, 140, dtype=dtype)
            first_mapped_value = 32
            lut_uid = UID()
            r_lut = PaletteColorLUT(
                first_mapped_value,
                r_lut_data,
                color='red',
            )
            g_lut = PaletteColorLUT(
                first_mapped_value,
                g_lut_data,
                color='green',
            )
            b_lut = PaletteColorLUT(
                first_mapped_value,
                b_lut_data,
                color='blue',
            )
            instance = PaletteColorLUTTransformation(
                red_lut=r_lut,
                green_lut=g_lut,
                blue_lut=b_lut,
                palette_color_lut_uid=lut_uid,
            )
            assert instance.PaletteColorLookupTableUID == lut_uid
            red_desc = [len(r_lut_data), first_mapped_value, bits]
            r_lut_data_retrieved = np.frombuffer(
                instance.RedPaletteColorLookupTableData,
                dtype=dtype,
            )
            assert np.array_equal(r_lut_data, r_lut_data_retrieved)
            assert (
                instance.RedPaletteColorLookupTableDescriptor == red_desc
            )
            green_desc = [len(g_lut_data), first_mapped_value, bits]
            g_lut_data_retrieved = np.frombuffer(
                instance.GreenPaletteColorLookupTableData,
                dtype=dtype,
            )
            assert np.array_equal(g_lut_data, g_lut_data_retrieved)
            assert (
                instance.GreenPaletteColorLookupTableDescriptor == green_desc
            )
            blue_desc = [len(b_lut_data), first_mapped_value, bits]
            b_lut_data_retrieved = np.frombuffer(
                instance.BluePaletteColorLookupTableData,
                dtype=dtype,
            )
            assert np.array_equal(b_lut_data, b_lut_data_retrieved)
            assert (
                instance.BluePaletteColorLookupTableDescriptor == blue_desc
            )

            assert np.array_equal(instance.red_lut.lut_data, r_lut_data)
            assert np.array_equal(instance.green_lut.lut_data, g_lut_data)
            assert np.array_equal(instance.blue_lut.lut_data, b_lut_data)

            assert instance.first_mapped_value == first_mapped_value
            assert instance.number_of_entries == len(r_lut_data)
            assert instance.bits_per_entry == bits

            arr = np.array([32, 33, 32, 132])
            expected = np.array(
                [
                    [10, 11, 10, 110],
                    [20, 21, 20, 120],
                    [30, 31, 30, 130],
                ]
            ).T
            output = instance.apply(arr)
            assert np.array_equal(output, expected)

    def test_construction_no_uid(self):
        r_lut_data = np.arange(10, 120, dtype=np.uint16)
        g_lut_data = np.arange(20, 130, dtype=np.uint16)
        b_lut_data = np.arange(30, 140, dtype=np.uint16)
        first_mapped_value = 32
        r_lut = PaletteColorLUT(first_mapped_value, r_lut_data, color='red')
        g_lut = PaletteColorLUT(first_mapped_value, g_lut_data, color='green')
        b_lut = PaletteColorLUT(first_mapped_value, b_lut_data, color='blue')
        instance = PaletteColorLUTTransformation(
            red_lut=r_lut,
            green_lut=g_lut,
            blue_lut=b_lut,
        )
        assert not hasattr(instance, 'PaletteColorLookupTableUID')

    def test_construction_different_lengths(self):
        r_lut_data = np.arange(10, 120, dtype=np.uint16)
        g_lut_data = np.arange(20, 120, dtype=np.uint16)
        b_lut_data = np.arange(30, 120, dtype=np.uint16)
        first_mapped_value = 32
        r_lut = PaletteColorLUT(first_mapped_value, r_lut_data, color='red')
        g_lut = PaletteColorLUT(first_mapped_value, g_lut_data, color='green')
        b_lut = PaletteColorLUT(first_mapped_value, b_lut_data, color='blue')
        with pytest.raises(ValueError):
            PaletteColorLUTTransformation(
                red_lut=r_lut,
                green_lut=g_lut,
                blue_lut=b_lut,
            )

    def test_construction_different_dtypes(self):
        r_lut_data = np.arange(10, 120, dtype=np.uint8)
        g_lut_data = np.arange(20, 130, dtype=np.uint16)
        b_lut_data = np.arange(30, 140, dtype=np.uint16)
        first_mapped_value = 32
        r_lut = PaletteColorLUT(first_mapped_value, r_lut_data, color='red')
        g_lut = PaletteColorLUT(first_mapped_value, g_lut_data, color='green')
        b_lut = PaletteColorLUT(first_mapped_value, b_lut_data, color='blue')
        with pytest.raises(ValueError):
            PaletteColorLUTTransformation(
                red_lut=r_lut,
                green_lut=g_lut,
                blue_lut=b_lut,
            )

    def test_construction_different_first_values(self):
        r_lut_data = np.arange(10, 120, dtype=np.uint16)
        g_lut_data = np.arange(20, 130, dtype=np.uint16)
        b_lut_data = np.arange(30, 140, dtype=np.uint16)
        r_first_mapped_value = 32
        g_first_mapped_value = 24
        b_first_mapped_value = 32
        r_lut = PaletteColorLUT(r_first_mapped_value, r_lut_data, color='red')
        g_lut = PaletteColorLUT(g_first_mapped_value, g_lut_data, color='green')
        b_lut = PaletteColorLUT(b_first_mapped_value, b_lut_data, color='blue')
        with pytest.raises(ValueError):
            PaletteColorLUTTransformation(
                red_lut=r_lut,
                green_lut=g_lut,
                blue_lut=b_lut,
            )

    def test_construction_from_colors(self):
        lut = PaletteColorLUTTransformation.from_colors(
            ['black', 'red', 'green', 'blue', 'white'],
        )

        assert np.array_equal(lut.red_lut.lut_data, [0, 255, 0, 0, 255])
        assert np.array_equal(lut.green_lut.lut_data, [0, 0, 128, 0, 255])
        assert np.array_equal(lut.blue_lut.lut_data, [0, 0, 0, 255, 255])

    def test_construction_from_combined(self):

        r_lut_data = np.arange(10, 120, dtype=np.uint8)
        g_lut_data = np.arange(20, 130, dtype=np.uint8)
        b_lut_data = np.arange(30, 140, dtype=np.uint8)

        combined_lut = np.stack(
            [r_lut_data, g_lut_data, b_lut_data],
            axis=-1
        )
        lut = PaletteColorLUTTransformation.from_combined_lut(
            combined_lut,
        )

        assert np.array_equal(lut.red_lut.lut_data, r_lut_data)
        assert np.array_equal(lut.blue_lut.lut_data, b_lut_data)
        assert np.array_equal(lut.green_lut.lut_data, g_lut_data)


class TestSpecimenDescription(TestCase):
    def test_construction(self):
        specimen_id = 'specimen 1'
        specimen_uid = UID()
        instance = SpecimenDescription(
            specimen_id=specimen_id,
            specimen_uid=specimen_uid
        )
        assert instance.specimen_id == specimen_id
        assert instance.specimen_uid == specimen_uid
        assert instance.specimen_location is None
        assert len(instance.specimen_preparation_steps) == 0
        assert instance.specimen_type is None
        assert instance.specimen_short_description is None
        assert instance.specimen_detailed_description is None
        assert instance.issuer_of_specimen_id is None
        assert instance.primary_anatomic_structures is None

    def test_construction_optionals(self):
        specimen_id = 'specimen 1'
        specimen_uid = UID()
        specimen_location = "specimen location"
        specimen_type = CodedConcept(
            "specimen type",
            "test",
            "test specimen type"
        )
        specimen_short_description = "specimen short description"
        specimen_detailed_description = "specimen detailed description"
        issuer_of_specimen_id = IssuerOfIdentifier("issuer id")
        primary_anatomic_structures = [
            CodedConcept(
                "anatomic structure",
                "test",
                "test anatomic structure"
            )
        ]
        instance = SpecimenDescription(
            specimen_id=specimen_id,
            specimen_uid=specimen_uid,
            specimen_location=specimen_location,
            issuer_of_specimen_id=issuer_of_specimen_id,
            primary_anatomic_structures=primary_anatomic_structures,
            specimen_type=specimen_type,
            specimen_short_description=specimen_short_description,
            specimen_detailed_description=specimen_detailed_description,
        )
        assert instance.specimen_location == specimen_location
        assert instance.specimen_type == specimen_type
        assert instance.specimen_short_description == specimen_short_description
        assert (
            instance.specimen_detailed_description ==
            specimen_detailed_description
        )
        assert (
            instance.issuer_of_specimen_id == issuer_of_specimen_id
        )
        assert (
            instance.primary_anatomic_structures == primary_anatomic_structures
        )

    def test_construction_with_to_long_short_description(self):
        specimen_id = 'specimen 1'
        specimen_uid = UID()
        specimen_short_description = "x" * 65
        with pytest.raises(ValueError):
            SpecimenDescription(
                specimen_id=specimen_id,
                specimen_uid=specimen_uid,
                specimen_short_description=specimen_short_description
            )

    def test_construction_with_backslash_in_short_description(self):
        specimen_id = 'specimen 1'
        specimen_uid = UID()
        specimen_short_description = 'short_description_with_backslash\\'
        with pytest.raises(ValueError):
            SpecimenDescription(
                specimen_id=specimen_id,
                specimen_uid=specimen_uid,
                specimen_short_description=specimen_short_description
            )

    def test_construction_with_code_specimen_type(self):
        specimen_id = 'specimen 1'
        specimen_uid = UID()
        specimen_type = Code(
            "specimen type",
            "test",
            "test specimen type"
        )
        instance = SpecimenDescription(
            specimen_id=specimen_id,
            specimen_uid=specimen_uid,
            specimen_type=specimen_type,
        )
        assert isinstance(instance.specimen_type, CodedConcept)
        assert instance.specimen_type == specimen_type

    def test_construction_with_preparation_steps(self):
        parent_specimen_id = 'surgical specimen'
        specimen_id = 'section specimen'
        specimen_uid = UID()
        specimen_collection = SpecimenCollection(procedure=codes.SCT.Biopsy)
        specimen_sampling = SpecimenSampling(
            method=codes.SCT.BlockSectioning,
            parent_specimen_id=parent_specimen_id,
            parent_specimen_type=codes.SCT.GrossSpecimen
        )
        specimen_staining = SpecimenStaining(
            substances=[
                codes.SCT.HematoxylinStain,
                codes.SCT.WaterSolubleEosinStain,
            ]
        )
        instance = SpecimenDescription(
            specimen_id=specimen_id,
            specimen_uid=specimen_uid,
            specimen_preparation_steps=[
                SpecimenPreparationStep(
                    specimen_id=parent_specimen_id,
                    processing_procedure=specimen_collection,
                ),
                SpecimenPreparationStep(
                    specimen_id=specimen_id,
                    processing_procedure=specimen_sampling,
                ),
                SpecimenPreparationStep(
                    specimen_id=specimen_id,
                    processing_procedure=specimen_staining,
                ),
            ]
        )
        assert instance.specimen_id == specimen_id
        assert instance.specimen_uid == specimen_uid
        assert len(instance.specimen_preparation_steps) == 3

    def test_construction_from_dataset(self):
        specimen_id = 'specimen 1'
        specimen_uid = UID()
        dataset = Dataset()
        dataset.SpecimenIdentifier = specimen_id
        dataset.SpecimenUID = str(specimen_uid)
        dataset.IssuerOfTheSpecimenIdentifierSequence = []
        dataset.SpecimenPreparationSequence = []
        dataset_reread = write_and_read_dataset(dataset)
        instance = SpecimenDescription.from_dataset(dataset_reread)
        assert instance.specimen_id == specimen_id
        assert instance.specimen_uid == specimen_uid
        assert len(instance.specimen_preparation_steps) == 0

    def test_construction_from_dataset_with_optionals(self):
        specimen_id = 'specimen 1'
        specimen_uid = UID()
        specimen_location = "specimen location"
        specimen_preparation_steps = [
            SpecimenPreparationStep(
                specimen_id,
                SpecimenCollection(procedure=codes.SCT.Biopsy)
            )
        ]
        specimen_type = CodedConcept(
            "specimen type",
            "test",
            "test specimen type"
        )
        specimen_short_description = "specimen short description"
        specimen_detailed_description = "specimen detailed description"
        issuer_of_specimen_id = IssuerOfIdentifier("issuer id")
        primary_anatomic_structures = [
            CodedConcept(
                "anatomic structure",
                "test",
                "test anatomic structure"
            )
        ]
        dataset = Dataset()
        dataset.SpecimenIdentifier = specimen_id
        dataset.SpecimenUID = str(specimen_uid)
        dataset.SpecimenLocalizationContentItemSequence = [
            TextContentItem(
                name=codes.DCM.LocationOfSpecimen,
                value=specimen_location
            )
        ]
        dataset.SpecimenTypeCodeSequence = [specimen_type]
        dataset.SpecimenPreparationSequence = specimen_preparation_steps
        dataset.SpecimenShortDescription = specimen_short_description
        dataset.SpecimenDetailedDescription = specimen_detailed_description
        dataset.IssuerOfTheSpecimenIdentifierSequence = [issuer_of_specimen_id]
        dataset.PrimaryAnatomicStructureSequence = primary_anatomic_structures
        dataset_reread = write_and_read_dataset(dataset)
        instance = SpecimenDescription.from_dataset(dataset_reread)
        assert instance.specimen_location == specimen_location
        assert instance.specimen_preparation_steps == specimen_preparation_steps
        assert instance.specimen_type == specimen_type
        assert instance.specimen_short_description == specimen_short_description
        assert (
            instance.specimen_detailed_description ==
            specimen_detailed_description
        )
        assert isinstance(instance.issuer_of_specimen_id, IssuerOfIdentifier)
        assert instance.issuer_of_specimen_id == issuer_of_specimen_id
        assert (
            instance.primary_anatomic_structures == primary_anatomic_structures
        )


class TestIssuerOfIdentifier(TestCase):
    def test_construction(self):
        issuer_of_identifier = "issuer of identifier"
        instance = IssuerOfIdentifier(issuer_of_identifier)
        assert instance.issuer_of_identifier == issuer_of_identifier
        assert instance.issuer_of_identifier_type is None

    def test_construction_with_optionals(self):
        issuer_of_identifier = "issuer of identifier id"
        issuer_of_identifier_type = UniversalEntityIDTypeValues.DNS
        instance = IssuerOfIdentifier(
            issuer_of_identifier,
            issuer_of_identifier_type
        )
        assert instance.issuer_of_identifier == issuer_of_identifier
        assert instance.issuer_of_identifier_type == issuer_of_identifier_type

    def test_construction_from_dataset(self):
        issuer_of_identifier = "issuer of identifier"
        dataset = Dataset()
        dataset.LocalNamespaceEntityID = issuer_of_identifier
        dataset_reread = write_and_read_dataset(dataset)
        instance = IssuerOfIdentifier.from_dataset(dataset_reread)
        assert isinstance(instance, IssuerOfIdentifier)
        assert instance.issuer_of_identifier == issuer_of_identifier
        assert instance.issuer_of_identifier_type is None

    def test_construction_from_dataset_with_optionals(self):
        issuer_of_identifier = "issuer of identifier"
        issuer_of_identifier_type = UniversalEntityIDTypeValues.DNS
        dataset = Dataset()
        dataset.UniversalEntityID = issuer_of_identifier
        dataset.UniversalEntityIDType = issuer_of_identifier_type.value
        dataset_reread = write_and_read_dataset(dataset)
        instance = IssuerOfIdentifier.from_dataset(dataset_reread)
        assert isinstance(instance, IssuerOfIdentifier)
        assert instance.issuer_of_identifier == issuer_of_identifier
        assert instance.issuer_of_identifier_type == issuer_of_identifier_type
