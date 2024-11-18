"""Chem/RDKIT/Mordred utilities for Sageworks"""

import numpy as np
import pandas as pd
import logging

logger = logging.getLogger("sageworks")

# Third Party Imports
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, AllChem
    from rdkit.ML.Descriptors import MoleculeDescriptors
    from rdkit import RDLogger

    # Turn off warnings for RDKIT (revisit this)
    RDLogger.DisableLog("rdApp.*")
    NO_RDKIT = False
except ImportError:
    print("RDKit Python module not found! pip install rdkit")
    NO_RDKIT = True

try:
    from mordred import Calculator
    from mordred import AcidBase, Aromatic, Polarizability, RotatableBond

    NO_MORDRED = False
except ImportError:
    print("Mordred Python module not found! pip install mordred")
    NO_MORDRED = True


def micromolar_to_log(series_µM: pd.Series) -> pd.Series:
    """
    Convert a pandas Series of concentrations in µM (micromolar) to their logarithmic values (log10).

    Parameters:
    series_uM (pd.Series): Series of concentrations in micromolar.

    Returns:
    pd.Series: Series of logarithmic values (log10).
    """
    # Replace 0 or negative values with a small number to avoid log errors
    adjusted_series = series_µM.clip(lower=1e-9)  # Alignment with another project

    series_mol_per_l = adjusted_series * 1e-6  # Convert µM/L to mol/L
    log_series = np.log10(series_mol_per_l)
    return log_series


def log_to_micromolar(log_series: pd.Series) -> pd.Series:
    """
    Convert a pandas Series of logarithmic values (log10) back to concentrations in µM (micromolar).

    Parameters:
    log_series (pd.Series): Series of logarithmic values (log10).

    Returns:
    pd.Series: Series of concentrations in micromolar.
    """
    series_mol_per_l = 10**log_series  # Convert log10 back to mol/L
    series_µM = series_mol_per_l * 1e6  # Convert mol/L to µM
    return series_µM


def log_to_category(log_series: pd.Series) -> pd.Series:
    """
    Convert a pandas Series of log values to concentration categories.

    Parameters:
    log_series (pd.Series): Series of logarithmic values (log10).

    Returns:
    pd.Series: Series of concentration categories.
    """
    # Create a solubility classification column
    bins = [-float("inf"), -5, -4, float("inf")]
    labels = ["low", "medium", "high"]
    return pd.cut(log_series, bins=bins, labels=labels)


def compute_molecular_descriptors(df: pd.DataFrame) -> pd.DataFrame:
    """Compute and add all the Molecular Descriptors

    Args:
        df(pd.DataFrame): The DataFrame to process and generate RDKit/Mordred Descriptors

    Returns:
        pd.DataFrame: The input DataFrame with all the RDKit Descriptors added
    """

    # Check for the smiles column (any capitalization)
    smiles_column = next((col for col in df.columns if col.lower() == "smiles"), None)
    if smiles_column is None:
        raise ValueError("Input DataFrame must have a 'smiles' column")

    # Compute/add all the Molecular Descriptors
    print("Computing Molecular Descriptors...")

    # Conversion to Molecules
    molecules = [Chem.MolFromSmiles(smile) for smile in df[smiles_column]]

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
    output_df = pd.concat([df, rdkit_features_df, mordred_df], axis=1)

    # Return the DataFrame with the RDKit and Mordred Descriptors added
    return output_df


def compute_morgan_fingerprints(df: pd.DataFrame, radius=2, nBits=2048) -> pd.DataFrame:
    """Compute and add Morgan fingerprints to the DataFrame.

    Args:
        df (pd.DataFrame): Input DataFrame containing SMILES strings.
        radius (int): Radius for the Morgan fingerprint.
        nBits (int): Number of bits for the fingerprint.

    Returns:
        pd.DataFrame: The input DataFrame with the Morgan fingerprints added as bit strings.
    """

    # Check for the SMILES column (case-insensitive)
    smiles_column = next((col for col in df.columns if col.lower() == "smiles"), None)
    if smiles_column is None:
        raise ValueError("Input DataFrame must have a 'smiles' column")

    # Convert SMILES to RDKit molecule objects (vectorized)
    molecules = df[smiles_column].apply(Chem.MolFromSmiles)

    # Handle invalid molecules
    invalid_smiles = molecules.isna()
    if invalid_smiles.any():
        logger.critical(f"Invalid SMILES strings found at indices: {df.index[invalid_smiles].tolist()}")
        molecules = molecules.dropna()
        df = df.loc[molecules.index].reset_index(drop=True)

    # Compute Morgan fingerprints (vectorized)
    fingerprints = molecules.apply(
        lambda mol: (
            AllChem.GetMorganFingerprintAsBitVect(mol, radius=radius, nBits=nBits).ToBitString() if mol else None
        )
    )

    # Add the fingerprints to the DataFrame
    df["morgan_fingerprint"] = fingerprints
    return df


if __name__ == "__main__":

    # Fake molecule
    smiles = "CC(CN1CC(C)OC(C)C1)"

    # Test the concentration conversion functions
    df = pd.DataFrame({"smiles": [smiles, smiles, smiles, smiles, smiles, smiles], "µM": [500, 50, 5, 1, 0.1, 0]})

    # Convert µM to log10
    df["log10"] = micromolar_to_log(df["µM"])
    print(df)

    # Convert log10 back to µM
    df["µM_new"] = log_to_micromolar(df["log10"])
    print(df)

    # Convert log10 to categories
    df["category"] = log_to_category(df["log10"])
    print(df)

    # Compute Molecular Descriptors
    df = pd.DataFrame({"smiles": [smiles, smiles, smiles, smiles, smiles]})
    df = compute_molecular_descriptors(df)
    print(df)

    # Compute Morgan Fingerprints
    df = compute_morgan_fingerprints(df)
    print(df)
