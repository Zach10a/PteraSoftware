
# ToDo: Properly document this module.
"""This is a testing case for the steady horseshoe vortex lattice method solver.

    Based on an identical XFLR5 testing case, the expected output for this case is:
        CL:     0.790
        CDi:    0.019
        Cl:     0.000
        Cm:     -0.690
        Cn:     0.000

    Note: The expected output was created using XFLR5's inviscid VLM1 analysis type, which is a horseshoe vortex
    lattice method solver.
"""

import unittest
import tests.integration
import aviansoftwareminimumviableproduct as asmvp
import pyvista as pv
from unittest import mock


# ToDo: Properly document this class.
class TestSteadyHorseshoeVortexLatticeMethod(unittest.TestCase):
    """

    """

    # ToDo: Properly document this method.
    def setUp(self):
        """

        :return:
        """

        self.steady_horseshoe_vortex_lattice_method_validation_solver = (
            tests.integration.fixtures.solver_fixtures.make_steady_horseshoe_vortex_lattice_method_validation_solver()
        )

    # ToDo: Properly document this method.
    def tearDown(self):
        """

        :return:
        """

        del self.steady_horseshoe_vortex_lattice_method_validation_solver

    # ToDo: Properly document this method.
    def test_method(self):
        """

        :return:
        """

        # Run the solver.
        self.steady_horseshoe_vortex_lattice_method_validation_solver.run(verbose=False)

        CDi_expected = 0.019
        CDi_error = abs(self.steady_horseshoe_vortex_lattice_method_validation_solver.CDi - CDi_expected) / CDi_expected

        CL_expected = 0.790
        CL_error = abs(self.steady_horseshoe_vortex_lattice_method_validation_solver.CL - CL_expected) / CL_expected

        Cl_expected = 0.000
        Cl_error = abs(self.steady_horseshoe_vortex_lattice_method_validation_solver.Cl - Cl_expected)

        Cm_expected = -0.690
        Cm_error = abs(self.steady_horseshoe_vortex_lattice_method_validation_solver.Cm - Cm_expected) / Cm_expected

        Cn_expected = 0.000
        Cn_error = abs(self.steady_horseshoe_vortex_lattice_method_validation_solver.Cn - Cn_expected)

        allowable_error = 0.05

        self.assertTrue(CDi_error < allowable_error)
        self.assertTrue(CL_error < allowable_error)
        self.assertTrue(Cl_error < allowable_error)
        self.assertTrue(Cm_error < allowable_error)
        self.assertTrue(Cn_error < allowable_error)

    def test_output(self):

        plotter = pv.Plotter

        with unittest.mock.patch.object(plotter, 'show') as mocked_plotter_show:
            asmvp.output.draw(
                self.steady_horseshoe_vortex_lattice_method_validation_solver.airplane,
                show_delta_pressures=False,
                show_streamlines=False
            )

        assert mocked_plotter_show.call_count == 1
