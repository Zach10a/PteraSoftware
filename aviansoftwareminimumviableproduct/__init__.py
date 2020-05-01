"""This package contains all the source code for the Avian Software Minimum Viable Product project.

This package contains the following subpackages:
    None

This package contains the following directories:
    airfoils: This folder contains a collection of airfoils whose coordinates are stored in DAT files.

This package contains the following modules:
    __init__.py: This module is this packages initialization script. It imports all the modules from this package.
    aerodynamics.py: This module contains useful aerodynamics functions, and the vortex class definitions.
    geometry.py: This module contains useful functions that relate to geometry, and the class definitions for different
                 types of geometries.
    meshing.py: This module contains useful functions for creating meshes.
    output.py: This module contains useful functions for visualizing solutions to problems.
    performance.py: This module contains the class definitions for the geometry's movement and the problem's operating
                    point.
    problems.py: This module contains the class definitions for different types of problems.
    steady_vortex_lattice_method.py: This module contains the class definition of this package's steady vortex lattice
                                     solver.
    unsteady_vortex_lattice_method.py: This module contains the class definition for this package's unsteady vortex
                                       lattice solver.
"""

from aviansoftwareminimumviableproduct import aerodynamics
from aviansoftwareminimumviableproduct import problems
from aviansoftwareminimumviableproduct import geometry
from aviansoftwareminimumviableproduct import meshing
from aviansoftwareminimumviableproduct import performance
from aviansoftwareminimumviableproduct import output
from aviansoftwareminimumviableproduct import steady_vortex_lattice_method
