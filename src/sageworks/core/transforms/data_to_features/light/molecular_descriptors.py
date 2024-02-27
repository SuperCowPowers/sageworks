"""MolecularDescriptors: Compute a Feature Set based on RDKit Descriptors"""

import sys
import pandas as pd

# Local Imports
from sageworks.core.transforms.data_to_features.light.data_to_features_light import (
    DataToFeaturesLight,
)
from sageworks.utils import pandas_utils

# Third Party Imports
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors
    from rdkit.ML.Descriptors import MoleculeDescriptors
    from rdkit import RDLogger
except ImportError:
    print("RDKit Python module not found! pip install rdkit")
    sys.exit(0)

try:
    from mordred import Calculator
    from mordred import AcidBase, Aromatic, Polarizability, RotatableBond
except ImportError:
    print("Mordred Python module not found! pip install mordred")
    sys.exit(0)


class MolecularDescriptors(DataToFeaturesLight):
    """MolecularDescriptors: Create a FeatureSet (RDKit Descriptors) from a DataSource

    Common Usage:
        ```
        to_features = MolecularDescriptors(data_uuid, feature_uuid)
        to_features.set_output_tags(["aqsol", "whatever"])
        to_features.transform()
        ```
    """

    def __init__(self, data_uuid: str, feature_uuid: str):
        """MolecularDescriptors Initialization

        Args:
            data_uuid (str): The UUID of the SageWorks DataSource to be transformed
            feature_uuid (str): The UUID of the SageWorks FeatureSet to be created
        """

        # Call superclass init
        super().__init__(data_uuid, feature_uuid)

        # Turn off warnings for RDKIT (revisit this)
        RDLogger.DisableLog("rdApp.*")

    def transform_impl(self, **kwargs):
        """Compute a Feature Set based on RDKit Descriptors"""

        # Check the input DataFrame has the required columns
        if "smiles" not in self.input_df.columns:
            raise ValueError("Input DataFrame must have a 'smiles' column")

        # Compute/add all the Molecular Descriptors
        self.output_df = self.compute_molecular_descriptors(self.input_df)

        # Drop any NaNs (and INFs)
        self.output_df = pandas_utils.drop_nans(self.output_df, how="all")

    def compute_molecular_descriptors(self, process_df: pd.DataFrame) -> pd.DataFrame:
        """Compute and add all the Molecular Descriptors
        Args:
            process_df(pd.DataFrame): The DataFrame to process and generate RDKit Descriptors
        Returns:
            pd.DataFrame: The input DataFrame with all the RDKit Descriptors added
        """
        self.log.important("Computing Molecular Descriptors...")

        # Conversion to Molecules
        molecules = [Chem.MolFromSmiles(smile) for smile in process_df["smiles"]]

        # Now get all the RDKIT Descriptors
        all_descriptors = [x[0] for x in Descriptors._descList]

        # There's an overflow issue that happens with the IPC descriptor, so we'll remove it
        # See: https://github.com/rdkit/rdkit/issues/1527
        if "Ipc" in all_descriptors:
            all_descriptors.remove("Ipc")

        # Make sure we don't have duplicates
        all_descriptors = list(set(all_descriptors))

        # Super useful Molecular Descriptor Calculator Class
        calc = MoleculeDescriptors.MolecularDescriptorCalculator(all_descriptors)
        column_names = calc.GetDescriptorNames()
        descriptor_values = [calc.CalcDescriptors(m) for m in molecules]
        rdkit_features_df = pd.DataFrame(descriptor_values, columns=column_names)

        # Now compute Mordred Features
        descriptor_choice = [AcidBase, Aromatic, Polarizability, RotatableBond]
        calc = Calculator()
        for des in descriptor_choice:
            calc.register(des)
        mordred_df = calc.pandas(molecules, nproc=1)

        # Return the DataFrame with the RDKit and Mordred Descriptors added
        return pd.concat([process_df, rdkit_features_df, mordred_df], axis=1)


if __name__ == "__main__":
    """Exercise the MolecularDescriptors Class"""
    from sageworks.api.data_source import DataSource

    full_test = True

    # Unit Test: Create the class with inputs
    unit_test = MolecularDescriptors("aqsol_data", "aqsol_mol_descriptors")
    unit_test.input_df = DataSource("aqsol_data").pull_dataframe()[:100]
    unit_test.transform_impl()
    output_df = unit_test.output_df
    print(output_df.shape)
    print(output_df.head())

    # Full Test: Create the class with inputs and outputs and invoke the transform
    if full_test:
        data_to_features = MolecularDescriptors("aqsol_data", "aqsol_mol_descriptors")
        data_to_features.set_output_tags(["logS", "public"])
        query = 'SELECT id, "group", solubility, smiles FROM aqsol_data'
        data_to_features.transform(target_column="solubility", id_column="id", query=query)
