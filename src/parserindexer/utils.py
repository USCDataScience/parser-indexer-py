# -*- coding: utf-8 -*-
import re
import logging

# Redirect warnings from stderr to Python standard logging (e.g., warnings
# raised by `warnings.warn()` will be directly write to the log file)
logging.captureWarnings(True)

# Map target aliases to canonical names
targettab = {
    # MPF
    'B._Bill': 'Barnacle_Bill',
    'Bakers_Bench': "Baker's_Bench",
    'Bambam': 'Bam_Bam',
    'Bamm_Bamm': 'Bam_Bam',
    'Fat_Top': 'Flat_Top',
    'Garak': 'Garrak',
    'Ga_Rrak': 'Garrak',
    'H._Dome': 'Half_Dome',
    'Hobbs': 'Hobbes',
    'Mini-Matterhorn': 'Mini_Matterhorn',
    'Mm': 'Mini_Matterhorn',
    'Poohbear': 'Pooh_Bear',
    'Scooby': 'Scooby_Doo',
    'Souffl': 'Soufflé',
    'Souffle': 'Soufflé',
    "Souffle'": 'Soufflé',
    'Soufle': 'Soufflé',
    # PHX
    'Bb': 'Baby_Bear',
    'Bc': 'Burning_Coals',
    'Bears_Lodge': "Bear's_Lodge",
    'Dg': 'Dodo_Goldilocks',
    'D_G': 'Dodo_Goldilocks',
    'Dodo': 'Dodo_Goldilocks',
    'Dodogoldilocks': 'Dodo_Goldilocks',
    'Dodo-goldilocks': 'Dodo_Goldilocks',
    'Dodogoldilocks_Trench': 'Dodo_Goldilocks_Trench',
    'Dodo-goldilocks_Trench': 'Dodo_Goldilocks_Trench',
    'Dodo-Goldilocks_Trench': 'Dodo_Goldilocks_Trench',
    'Dodo_Trench': 'Dodo_Goldilocks_Trench',
    'Lamancha': 'La_Mancha',
    'Mamma_Bear': 'Mama_Bear',
    'Mancha': 'La_Mancha',
    'Rr': 'Rosy_Red',
    'Rr1': 'Rosy_Red',
    'Rr2': 'Rosy_Red',
    'Ww': 'Wicked_Witch'
    }

# Elements symbol table
symtab = {
    'Ac': 'Actinium',
    'Ag': 'Silver',
    'Al': 'Aluminum',
    'Am': 'Americium',
    'Ar': 'Argon',
    'As': 'Arsenic',
    'At': 'Astatine',
    'Au': 'Gold',
    'B': 'Boron',
    'Ba': 'Barium',
    'Be': 'Beryllium',
    'Bh': 'Bohrium',
    'Bi': 'Bismuth',
    'Bk': 'Berkelium',
    'Br': 'Bromine',
    'C': 'Carbon',
    'Ca': 'Calcium',
    'Cd': 'Cadmium',
    'Ce': 'Cerium',
    'Cf': 'Californium',
    'Cl': 'Chlorine',
    'Cm': 'Curium',
    'Cn': 'Copernicium',
    'Co': 'Cobalt',
    'Cr': 'Chromium',
    'Cs': 'Cesium',
    'Cu': 'Copper',
    'Db': 'Dubnium',
    'Ds': 'Darmstadtium',
    'Dy': 'Dysprosium',
    'Er': 'Erbium',
    'Es': 'Einsteinium',
    'Eu': 'Europium',
    'F': 'Fluorine',
    'Fe': 'Iron',
    'Fl': 'Flerovium',
    'Fm': 'Fermium',
    'Fr': 'Francium',
    'Ga': 'Gallium',
    'Gd': 'Gadolinium',
    'Ge': 'Germanium',
    'H': 'Hydrogen',
    'He': 'Helium',
    'Hf': 'Hafnium',
    'Hg': 'Mercury',
    'Ho': 'Holmium',
    'Hs': 'Hassium',
    'I': 'Iodine',
    'In': 'Indium',
    'Ir': 'Iridium',
    'K': 'Potassium',
    'Kr': 'Krypton',
    'La': 'Lanthanum',
    'Li': 'Lithium',
    'Lr': 'Lawrencium',
    'Lu': 'Lutetium',
    'Lv': 'Livermorium',
    'Md': 'Mendelevium',
    'Mg': 'Magnesium',
    'Mn': 'Manganese',
    'Mo': 'Molybdenum',
    'Mt': 'Meitnerium',
    'N': 'Nitrogen',
    'Na': 'Sodium',
    'Nb': 'Niobium',
    'Nd': 'Neodymium',
    'Ne': 'Neon',
    'Ni': 'Nickel',
    'No': 'Nobelium',
    'Np': 'Neptunium',
    'O': 'Oxygen',
    'Os': 'Osmium',
    'P': 'Phosphorus',
    'Pa': 'Protactinium',
    'Pb': 'Lead',
    'Pd': 'Palladium',
    'Pm': 'Promethium',
    'Po': 'Polonium',
    'Pr': 'Praseodymium',
    'Pt': 'Platinum',
    'Pu': 'Plutonium',
    'Ra': 'Radium',
    'Rb': 'Rubidium',
    'Re': 'Rhenium',
    'Rf': 'Rutherfordium',
    'Rg': 'Roentgenium',
    'Rh': 'Rhodium',
    'Rn': 'Radon',
    'Ru': 'Ruthenium',
    'S': 'Sulfur',
    'Sb': 'Antimony',
    'Sc': 'Scandium',
    'Se': 'Selenium',
    'Sg': 'Seaborgium',
    'Si': 'Silicon',
    'Sm': 'Samarium',
    'Sn': 'Tin',
    'Sr': 'Strontium',
    'Ta': 'Tantalum',
    'Tb': 'Terbium',
    'Tc': 'Technetium',
    'Te': 'Tellurium',
    'Th': 'Thorium',
    'Ti': 'Titanium',
    'Tl': 'Thallium',
    'Tm': 'Thulium',
    'U': 'Uranium',
    'Uuo': 'Ununoctium',
    'Uup': 'Ununpentium',
    'Uus': 'Ununseptium',
    'Uut': 'Ununtrium',
    'V': 'Vanadium',
    'W': 'Tungsten',
    'Xe': 'Xenon',
    'Y': 'Yttrium',
    'Yb': 'Ytterbium',
    'Zn': 'Zinc',
    'Zr': 'Zirconium'
}


def canonical_name(name):
    """
    Gets canonical name
    :param name - name whose canonical name is to be looked up
    :return canonical name
    """
    name = name.strip()
    if len(name) <= 3 and name.title() in symtab:
        return symtab[name.title()]
    else:
        return re.sub(r"[\s_-]+", " ", name).title().replace(' ', '_')


def canonical_target_name(name, id, targets, aliases):
    """
    Gets canonical target name
    :param name - name whose canonical name is to be looked up
    :return canonical name
    """
    name = name.strip()
    # Look up 'name' in the aliases; if found, replace with its antecedent
    # Note: this is super permissive.  Exact match on id is safe,
    # but we're also allowing any exact-text match with any other 
    # known target name.
    all_targets = [t['annotation_id_s'] for t in targets 
                   if t['name'] == name]
    name_aliases = [a['arg2_s'] for a in aliases 
                    if ((a['arg1_s'] == id) or 
                        (a['arg1_s'] in all_targets))]
    if len(name_aliases) > 0:
        # Ideally there is only one; let's use the first one
        can_name = [t['name'] for t in targets
                    if t['annotation_id_s'] == name_aliases[0]]
        print('Mapping <%s> to <%s>' % (name, can_name[0]))
        name = can_name[0]

    return re.sub(r"[\s_-]+", " ", name).title().replace(' ', '_')

def canonical_component_name(name):
    """
    This function gets canonical name for a component (either element/mineral): 
    """
    # remove hypen, unserscore, and extra space 
    name = " ".join(re.sub(r"[-_]", " ",name).split())
    name = " ".join([canonical_name(k) for k in name.split()])
    return name

class LogUtil(object):
    def __init__(self, log_file, filemode='w'):
        fmt = logging.Formatter(fmt='%(asctime)-15s: %(message)s',
                                datefmt='[%Y-%m-%d %H:%M:%S]')
        handler = logging.FileHandler(log_file, mode=filemode)
        handler.setFormatter(fmt)
        logger = logging.getLogger('py.warnings')
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        self.logger = logger

    def info(self, message):
        self.logger.info(message)

    def error(self, exception):
        self.logger.error(exception, exc_info=True)
