"""UK Government GHG conversion factors - the cells this ledger reaches.

From the "Factors by Category" sheet of the flat-file edition published for
each reporting year, kg CO2e rows. Keyed edition year -> the sheet's own
seven-part category tuple:

    (scope, level 1, level 2, level 3, level 4, column text, UOM)

Level 4 is empty for most rows but carries "kWh" on the electricity rows,
which is why a lookup that misses is retried with it.
"""

FACTORS = {
    2024: {
        ('Scope 1', 'Bioenergy', 'Biogas', 'Biogas', '', '', 'tonnes'):
            '1.26431',
        ('Scope 1', 'Bioenergy', 'Biomass', 'Wood pellets', '', '', 'tonnes'):
            '54.336539999999999',
        ('Scope 1', 'Fuels', 'Gaseous fuels', 'Natural gas', '', '', 'cubic metres'):
            '2.04542',
        ('Scope 1', 'Fuels', 'Liquid fuels', 'Petrol (average biofuel blend)', '', '', 'litres'):
            '2.0844',
        ('Scope 3', 'Material use', 'Paper', 'Paper and board: board', '', 'Primary material production', 'tonnes'):
            '1193.96586',
        ('Scope 3', 'Waste disposal', 'Refuse', 'Organic: food and drink waste', '', 'Composting', 'tonnes'):
            '8.8838600000000003',
        ('Scope 3', 'Water supply', 'Water supply', 'Water supply', '', '', 'cubic metres'):
            '0.15311',
        ('Scope 3', 'Water treatment', 'Water treatment', 'Water treatment', '', '', 'cubic metres'):
            '0.18573999999999999',
    },
    2025: {
        ('Scope 1', 'Bioenergy', 'Biomass', 'Grass/straw', '', '', 'tonnes'):
            '47.357089999999999',
        ('Scope 1', 'Fuels', 'Gaseous fuels', 'Natural gas', '', '', 'cubic metres'):
            '2.0667200000000001',
        ('Scope 1', 'Fuels', 'Liquid fuels', 'Petrol (average biofuel blend)', '', '', 'litres'):
            '2.0691600000000001',
        ('Scope 3', 'Transmission and distribution', 'T&D- UK electricity', 'Electricity: UK', 'kWh', '', 'kWh'):
            '0.018530000000000001',
        ('Scope 3', 'Waste disposal', 'Construction', 'Insulation', '', 'Landfill', 'tonnes'):
            '1.2633799999999999',
        ('Scope 3', 'Waste disposal', 'Plastic', 'Plastics: average plastics', '', 'Closed-loop', 'tonnes'):
            '4.6856799999999996',
    },
}
