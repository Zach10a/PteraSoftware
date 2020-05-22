"""This module contains the class definition of this package's steady horseshoe vortex lattice solver.

This module contains the following classes:
    SteadyHorseshoeVortexLatticeMethodSolver: This is an aerodynamics solver that uses a steady horseshoe vortex lattice
                                              method.

This module contains the following exceptions:
    None

This module contains the following functions:
    None
"""

import numpy as np
import aviansoftwareminimumviableproduct as asmvp


class SteadyHorseshoeVortexLatticeMethodSolver:
    """This is an aerodynamics solver that uses a steady horseshoe vortex lattice method.

    Citation:
        Adapted from:         aerodynamics.vlm3.py in AeroSandbox
        Author:               Peter Sharpe
        Date of Retrieval:    04/28/2020

    This class contains the following public methods:
        run: Run the solver on the steady problem.
        initialize_panel_vortices: This method calculates the locations of the vortex vertices, and then initializes the
                                   panels' vortices.
        set_up_geometry: Find the matrix of aerodynamic influence coefficients associated with this problem's geometry.
        set_up_operating_point: Find the normal freestream speed at every collocation point without the influence of the
                                vortices.
        calculate_vortex_strengths: Solve for each panels' vortex strength.
        calculate_solution_velocity: Find the velocity at a given point due to the freestream and the vortices.
        calculate_near_field_forces_and_moments: Find the the forces and moments calculated from the near field.
        calculate_streamlines: Calculates the location of the streamlines coming off the back of the wings.

    This class contains the following class attributes:
        None

    Subclassing:
        This class is not meant to be subclassed.
    """

    def __init__(self, steady_problem):
        """This is the initialization method.

        :param steady_problem: SteadyProblem
            This is the steady problem to be solved.
        :return: None
        """

        # Initialize this solution's attributes.
        self.steady_problem = steady_problem
        self.airplane = self.steady_problem.airplane
        self.operating_point = self.steady_problem.operating_point

        # Initialize empty attributes to hold aerodynamic data that pertains to this problem.
        self.aerodynamic_influence_coefficients = np.zeros((self.airplane.num_panels, self.airplane.num_panels))
        self.freestream_velocity = np.zeros(3)
        self.normal_directions = np.zeros((self.airplane.num_panels, 3))
        self.freestream_influences = np.zeros(self.airplane.num_panels)
        self.vortex_strengths = np.zeros(self.airplane.num_panels)
        self.total_near_field_force_wind_axes = np.zeros(3)
        self.total_near_field_moment_wind_axes = np.zeros(3)
        self.CDi = None
        self.CY = None
        self.CL = None
        self.Cl = None
        self.Cm = None
        self.Cn = None

    def run(self):
        """Run the solver on the steady problem.

        :return: None
        """

        # Initialize this problem's panels to have vortices congruent with this solver type.
        print("Initializing panel vortices...")
        self.initialize_panel_vortices()
        print("Panel vortices initialized.")

        # Find the matrix of aerodynamic influence coefficients associated with this problem's geometry.
        print("\nSetting up geometry...")
        self.set_up_geometry()
        print("Geometry set up.")

        # Find the normal freestream speed at every collocation point without vortices.
        print("\nSetting up operating point...")
        self.set_up_operating_point()
        print("Operating point set up.")

        # Solve for each panel's vortex strength.
        print("\nCalculating vortex strengths...")
        self.calculate_vortex_strengths()
        print("Vortex strengths calculated.")

        # Solve for the near field forces and moments on each panel.
        print("\nCalculating near field forces...")
        self.calculate_near_field_forces_and_moments()
        print("Near field forces calculated.")

        # Solve for the location of the streamlines coming off the back of the wings.
        print("\nCalculating streamlines...")
        self.calculate_streamlines()
        print("Streamlines calculated.")

        # Print out the total forces.
        print("\n\nForces in Wind Axes:")
        print("\tInduced Drag:\t\t\t", np.round(self.total_near_field_force_wind_axes[0], 3), " N")
        print("\tSide Force:\t\t\t\t", np.round(self.total_near_field_force_wind_axes[1], 3), " N")
        print("\tLift:\t\t\t\t\t", np.round(self.total_near_field_force_wind_axes[2], 3), " N")

        # Print out the total moments.
        print("\nMoments in Wind Axes:")
        print("\tRolling Moment:\t\t\t", np.round(self.total_near_field_moment_wind_axes[0], 3), " Nm")
        print("\tPitching Moment:\t\t", np.round(self.total_near_field_moment_wind_axes[1], 3), " Nm")
        print("\tYawing Moment:\t\t\t", np.round(self.total_near_field_moment_wind_axes[2], 3), " Nm")

        # Print out the coefficients.
        print("\nCoefficients in Wind Axes:")
        print("\tCDi:\t\t\t\t\t", np.round(self.CDi, 3))
        print("\tCY:\t\t\t\t\t\t", np.round(self.CY, 3))
        print("\tCL:\t\t\t\t\t\t", np.round(self.CL, 3))
        print("\tCl:\t\t\t\t\t\t", np.round(self.Cl, 3))
        print("\tCm:\t\t\t\t\t\t", np.round(self.Cm, 3))
        print("\tCn:\t\t\t\t\t\t", np.round(self.Cn, 3))

    def initialize_panel_vortices(self):
        """This method calculates the locations of the vortex vertices, and then initializes the panels' vortices.

        Every panel has a horseshoe vortex. The vortex's finite leg runs along the panel's quarter chord from right to
        left. It's infinite legs point backwards in the positive x direction.

        :return: None
        """

        # Find the freestream direction in geometry axes.
        freestream_direction = self.operating_point.calculate_freestream_direction_geometry_axes()

        # Iterate through the airplane's wings.
        for wing in self.airplane.wings:

            # Find a suitable length for the "infinite" legs of the horseshoe vortices on this wing. At twenty-times the
            # wing's span, these legs are essentially infinite.
            infinite_leg_length = wing.span * 20

            # Iterate through the wing's chordwise and spanwise panel positions.
            for chordwise_position in range(wing.num_chordwise_panels):
                for spanwise_position in range(wing.num_spanwise_panels):

                    # Pull the panel object out of the wing's list of panels.
                    panel = wing.panels[chordwise_position, spanwise_position]

                    # Find the location of the panel's front and right vortex vertices.
                    front_left_vortex_vertex = panel.front_left_vortex_vertex
                    front_right_vortex_vertex = panel.front_right_vortex_vertex

                    # Initialize the horseshoe vortex at this panel.
                    panel.horseshoe_vortex = (
                        asmvp.aerodynamics.HorseshoeVortex(
                            finite_leg_origin=front_right_vortex_vertex,
                            finite_leg_termination=front_left_vortex_vertex,
                            strength=None,
                            infinite_leg_direction=freestream_direction,
                            infinite_leg_length=infinite_leg_length
                        )
                    )

    def set_up_geometry(self):
        """Find the matrix of aerodynamic influence coefficients associated with this problem's geometry.

        :return: None
        """

        # Iterate through the airplane's wings. This wing contains the panel with the collocation point where the
        # vortex influence is to be calculated.
        for collocation_panel_wing in self.airplane.wings:

            # Convert the 2D ndarray of this wing's panels into a 1D list.
            collocation_panels = np.ravel(collocation_panel_wing.panels)

            # Iterate through the list of panels with the collocation points.
            for collocation_panel_index, collocation_panel in np.ndenumerate(collocation_panels):

                # Iterate through the airplane's wings. This wing contains the panel with the vortex whose influence
                # on the collocation point is to be calculated.
                for vortex_panel_wing in self.airplane.wings:

                    # Convert the 2D ndarray of this wing's panels into a 1D list.
                    vortex_panels = np.ravel(vortex_panel_wing.panels)

                    # Iterate through the list of panels with the vortices.
                    for vortex_panel_index, vortex_panel in np.ndenumerate(vortex_panels):

                        # Calculate the velocity induced at this collocation point by this vortex if the vortex's
                        # strength was 1.
                        normalized_induced_velocity_at_collocation_point = (
                            vortex_panel.calculate_normalized_induced_velocity(collocation_panel.collocation_point))

                        # Find the normal direction of the panel with the collocation point.
                        collocation_panel_normal_direction = collocation_panel.normal_direction

                        # Calculate the normal component of the velocity induced at this collocation point by this
                        # vortex if the vortex's strength was 1.
                        normal_normalized_induced_velocity_at_collocation_point = np.dot(
                            normalized_induced_velocity_at_collocation_point, collocation_panel_normal_direction)

                        # Add this value to the solver's aerodynamic influence coefficient matrix.
                        self.aerodynamic_influence_coefficients[collocation_panel_index, vortex_panel_index] = (
                            normal_normalized_induced_velocity_at_collocation_point)

    def set_up_operating_point(self):
        """Find the normal freestream speed at every collocation point without the influence of the vortices.

        :return: None
        """

        # This calculates and updates the direction the wind is going to, in geometry axes coordinates.
        self.freestream_velocity = np.expand_dims(self.operating_point.calculate_freestream_velocity_geometry_axes(), 0)

        # Iterate through the airplane's wings.
        for collocation_panel_wing in self.airplane.wings:

            # Convert the 2D ndarray of this wing's panels into a 1D list.
            collocation_panels = np.ravel(collocation_panel_wing.panels)

            # Iterate through the list of panels with the collocation points.
            for collocation_panel_index, collocation_panel in np.ndenumerate(collocation_panels):
                # Update the solver's list of normal directions.
                self.normal_directions[collocation_panel_index] = collocation_panel.normal_direction

                # Update solver's list of freestream influences.
                self.freestream_influences[collocation_panel_index] = (
                    np.dot(self.freestream_velocity, collocation_panel.normal_direction))

    def calculate_vortex_strengths(self):
        """Solve for each panel's vortex strength.

        :return: None
        """

        # Solve for the strength of each panel's vortex.
        self.vortex_strengths = np.linalg.solve(self.aerodynamic_influence_coefficients, -self.freestream_influences)

        # Iterate through the airplane's wings.
        for wing in self.airplane.wings:

            # Convert the 2D ndarray of this wing's panels into a 1D list.
            wing_panels = np.ravel(wing.panels)

            # Iterate through this list of panels.
            for panel_index, panel in np.ndenumerate(wing_panels):

                # Update each panel's vortex strength.
                panel.horseshoe_vortex.update_strength(self.vortex_strengths[panel_index])

    def calculate_solution_velocity(self, point):
        """Find the velocity at a given point due to the freestream and the vortices.

        :param point: 1D ndarray
            This is a vector containing the x, y, and z coordinates of the point to find the velocity at.
        :return: None
        """

        # Initialize an ndarray to hold the solution velocity.
        velocity_induced_by_vortices = np.zeros(3)

        # Iterate through the airplane's wings.
        for wing in self.airplane.wings:

            # Convert the 2D ndarray of this wing's panels into a 1D list.
            wing_panels = np.ravel(wing.panels)

            # Iterate through this list of panels.
            for panel in wing_panels:
                # Add the velocity induced by this panel's vortex at this point to the total induced velocity.
                velocity_induced_by_vortices += panel.calculate_induced_velocity(point)

        # Compute the freestream velocity in geometry axes.
        freestream = self.operating_point.calculate_freestream_velocity_geometry_axes()

        # Return the freestream velocity in geometry axes to the velocity induced by the vortices.
        return velocity_induced_by_vortices + freestream

    def calculate_near_field_forces_and_moments(self):
        """Find the the forces and moments calculated from the near field.

        :return: None
        """

        total_near_field_force_geometry_axes = np.zeros(3)
        total_near_field_moment_geometry_axes = np.zeros(3)

        # Iterate through the airplane's wings.
        for wing in self.airplane.wings:

            # Find the number of chordwise and spanwise panels in this wing.
            num_chordwise_panels = wing.num_chordwise_panels
            num_spanwise_panels = wing.num_spanwise_panels

            # Iterate through the chordwise and spanwise locations of the wing's panels.
            for chordwise_location in range(num_chordwise_panels):
                for spanwise_location in range(num_spanwise_panels):
                    # Find the panel at this location.
                    panel = wing.panels[chordwise_location, spanwise_location]

                    # Find the finite leg of this panel's horseshoe vortex.
                    bound_vortex = panel.horseshoe_vortex.finite_leg

                    # Calculate the velocity at the center of this finite leg.
                    velocity_at_vortex_center = self.calculate_solution_velocity(bound_vortex.center)

                    # Calculate the force and moment on this finite leg.
                    panel.near_field_force_geometry_axes = (
                            self.operating_point.density
                            * bound_vortex.strength
                            * np.cross(velocity_at_vortex_center, bound_vortex.vector)
                    )
                    panel.near_field_moment_geometry_axes = np.cross(bound_vortex.center - self.airplane.xyz_ref,
                                                                     panel.near_field_force_geometry_axes)

                    # Update the pressure on this panel.
                    panel.update_pressure()

                    total_near_field_force_geometry_axes += panel.near_field_force_geometry_axes
                    total_near_field_moment_geometry_axes += panel.near_field_moment_geometry_axes

        self.total_near_field_force_wind_axes = (
                np.transpose(self.operating_point.calculate_rotation_matrix_wind_axes_to_geometry_axes())
                @ total_near_field_force_geometry_axes
        )
        self.total_near_field_moment_wind_axes = (
                np.transpose(self.operating_point.calculate_rotation_matrix_wind_axes_to_geometry_axes())
                @ total_near_field_moment_geometry_axes
        )

        self.CDi = (
                -self.total_near_field_force_wind_axes[0]
                / self.operating_point.calculate_dynamic_pressure()
                / self.airplane.s_ref
        )
        self.CY = (
                self.total_near_field_force_wind_axes[1]
                / self.operating_point.calculate_dynamic_pressure()
                / self.airplane.s_ref
        )
        self.CL = (
                -self.total_near_field_force_wind_axes[2]
                / self.operating_point.calculate_dynamic_pressure()
                / self.airplane.s_ref
        )
        self.Cl = (
                self.total_near_field_moment_wind_axes[0]
                / self.operating_point.calculate_dynamic_pressure()
                / self.airplane.s_ref
                / self.airplane.b_ref
        )
        self.Cm = (
                self.total_near_field_moment_wind_axes[1]
                / self.operating_point.calculate_dynamic_pressure()
                / self.airplane.s_ref
                / self.airplane.c_ref
        )
        self.Cn = (
                self.total_near_field_moment_wind_axes[2]
                / self.operating_point.calculate_dynamic_pressure()
                / self.airplane.s_ref
                / self.airplane.b_ref
        )

    def calculate_streamlines(self):
        """Calculates the location of the streamlines coming off the back of the wings.

        :return: None
        """

        # Define the number of time steps to iterate through, and also the change in time, in seconds, between time
        # steps.
        num_steps = 100
        delta_time = 0.01

        # Iterate through the airplane's wings.
        for wing in self.airplane.wings:

            # Initialize an ndarray to hold the wing's streamline points.
            wing.streamline_points = np.zeros((num_steps + 1, wing.num_spanwise_panels, 3))

            # The chordwise position is along the trailing edge.
            chordwise_position = wing.num_chordwise_panels - 1

            # Increment through the wing's spanwise positions.
            for spanwise_position in range(wing.num_spanwise_panels):

                # Pull the panel object out of the wing's list of panels.
                panel = wing.panels[chordwise_position, spanwise_position]

                # Find the seed points, which are the midpoints of the back legs of the trailing edges of the vertices.
                seed_point = panel.back_left_vertex + 0.5 * (panel.back_right_vertex - panel.back_left_vertex)

                # Add the seed points as the first row in the wing's streamline point's array.
                wing.streamline_points[0, spanwise_position, :] = seed_point

                # Iterate through the time steps.
                for step in range(num_steps):
                    # Find the row of streamline points directly before the new row of streamline points.
                    last_point = wing.streamline_points[step, spanwise_position, :]

                    # Find and update the new row of streamline points.
                    wing.streamline_points[step + 1, spanwise_position, :] = (
                            last_point
                            + delta_time
                            * self.calculate_solution_velocity(last_point)
                    )
