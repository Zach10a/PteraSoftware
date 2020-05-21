"""This module contains the class definition of this package's steady ring vortex lattice solver.

This module contains the following classes:
    SteadyRingVortexLatticeMethodSolver: This is an aerodynamics solver that uses a steady ring vortex lattice method.

This module contains the following exceptions:
    None

This module contains the following functions:
    None
"""

import numpy as np
import aviansoftwareminimumviableproduct as asmvp


# ToDo: Properly cite document this class.
class SteadyRingVortexLatticeMethodSolver:
    """This is an aerodynamics solver that uses a steady ring vortex lattice method.

    Citation:
        Adapted from:         aerodynamics.vlm3.py in AeroSandbox
        Author:               Peter Sharpe
        Date of Retrieval:    04/28/2020

    This class contains the following public methods:
        run: Run the solver on the steady problem.
        set_up_geometry: Find the matrix of aerodynamic influence coefficients associated with this problem's geometry.
        set_up_operating_point: Find the normal freestream speed at every collocation point without vortices.
        calculate_vortex_strengths: Solve for each panel's vortex strength.
        calculate_solution_velocity: Find the velocity at a given point due to the freestream and the vortices.
        calculate_velocity_influences: Find the velocity at a given point due to the vorticity of every vortex if their
                                       strengths were all set to 1.0 meters squared per second.
        calculate_delta_cp: Find the change in the pressure coefficient between the upper and lower surfaces of a panel.
        calculate_near_field_forces_and_moments: Find the the forces and moments calculated from the near field.

    This class contains the following class attributes:
        None

    Subclassing:
        This class is not meant to be subclassed.
    """

    # ToDo: Properly cite document this method.
    def __init__(self, steady_problem):
        """This is the initialization method.

        :param steady_problem: SteadyProblem
            This is the steady problem's to be solved.
        """

        self.steady_problem = steady_problem
        self.airplane = self.steady_problem.airplane
        self.operating_point = self.steady_problem.operating_point

        # Initialize attributes to hold aerodynamic data that pertains to this problem.
        self.aerodynamic_influence_coefficients = np.zeros((self.airplane.num_panels, self.airplane.num_panels))
        self.freestream_velocity = np.zeros(3)
        self.normal_directions = np.zeros((self.airplane.num_panels, 3))
        self.freestream_influences = np.zeros(self.airplane.num_panels)
        self.vortex_strengths = np.zeros(self.airplane.num_panels)

    # ToDo: Properly document this method.
    def run(self):
        """Run the solver on the steady problem.

        :return: None
        """

        # Initialize this problem's panels to have vortices congruent with this solver type.
        print("Initializing panel vortices...")
        self.initialize_panel_vortices()
        print("Panel vortices initialized.")

        # Find the matrix of aerodynamic influence coefficients associated with this problem's geometry.
        print("Setting up geometry...")
        self.set_up_geometry()
        print("Geometry set up.")

        # Find the normal freestream speed at every collocation point without vortices.
        print("Setting up operating point...")
        self.set_up_operating_point()
        print("Operating point set up.")

        # Solve for each panel's vortex strength.
        print("Calculating vortex strengths...")
        self.calculate_vortex_strengths()
        print("Vortex strengths calculated.")

        # Solve for the near field forces and moments on each panel.
        print("Calculating near field forces...")
        self.calculate_near_field_forces_and_moments()
        print("Near field forces calculated.")

        # Solve for the location of the streamlines coming off the back of the wings.
        print("Calculating streamlines...")
        self.calculate_streamlines()
        print("Streamlines calculated.")

    # ToDo: Properly document this method.
    def initialize_panel_vortices(self):
        """This method calculates the locations of the vortex vertices, and then initializes the panel's vortices.

        This function takes in the type of problem this panel will be used in, and initializes the appropriate vortices.

        For the "steady horseshoe vortex lattice method" problem type:
            Every panel has a horseshoe vortex. The vortex's finite leg runs along the panel's quarter chord from right
            to left. It's infinite legs point backwards in the positive x direction.

        For the "steady ring vortex lattice method" problem type:
            The panel's ring vortex is a quadrangle whose front vortex leg is at the panel's quarter chord. The left and
            right vortex legs run along the panel's left and right legs. They extend backwards and meet the back vortex
            leg at one quarter chord back from the panel's back leg.

            Panels that are at the trailing edge of a wing have a horseshoe vortex in addition to their ring vortex. The
            horseshoe vortex's finite leg runs along the ring vortex's back leg but in the opposite direction. It's
            infinite legs point backwards in the positive x direction. The ring vortex and horseshoe vortex have the
            same strength, so the back leg of the ring vortex is cancelled.

        :return: None
        """

        freestream_direction = self.operating_point.calculate_freestream_direction_geometry_axes()

        for wing in self.airplane.wings:

            infinite_leg_length = wing.span() * 20

            # Increment through the wing's chordwise and spanwise positions.
            for chordwise_position in range(wing.num_chordwise_panels):
                for spanwise_position in range(wing.num_spanwise_panels):
                    # Pull the panel object out of the wing's list of panels.
                    panel = wing.panels[chordwise_position, spanwise_position]

                    front_left_vortex_vertex = panel.front_left_vortex_vertex
                    front_right_vortex_vertex = panel.front_right_vortex_vertex

                    if not panel.is_trailing_edge:
                        next_chordwise_panel = wing.panels[chordwise_position + 1, spanwise_position]
                        back_left_vortex_vertex = next_chordwise_panel.front_left_vortex_vertex
                        back_right_vortex_vertex = next_chordwise_panel.front_right_vortex_vertex
                    else:
                        back_left_vortex_vertex = front_left_vortex_vertex + (
                                panel.back_left_vertex - panel.front_left_vertex)
                        back_right_vortex_vertex = front_right_vortex_vertex + (
                                panel.back_right_vertex - panel.front_right_vertex)
                        panel.horseshoe_vortex = asmvp.aerodynamics.HorseshoeVortex(
                                finite_leg_origin=back_right_vortex_vertex,
                                finite_leg_termination=back_left_vortex_vertex,
                                strength=None,
                                infinite_leg_direction=freestream_direction,
                                infinite_leg_length=infinite_leg_length
                            )

                    # If the panel has a ring vortex, initialize it.
                    panel.ring_vortex = asmvp.aerodynamics.RingVortex(
                        front_right_vertex=front_right_vortex_vertex,
                        front_left_vertex=front_left_vortex_vertex,
                        back_left_vertex=back_left_vortex_vertex,
                        back_right_vertex=back_right_vortex_vertex,
                        strength=None
                    )

    # ToDo: Properly document this method.
    def set_up_geometry(self):
        """

        :return:
        """

        for collocation_panel_wing in self.airplane.wings:

            collocation_panel_wings_panels = np.ravel(collocation_panel_wing.panels)
            for collocation_panel_index, collocation_panel in np.ndenumerate(collocation_panel_wings_panels):

                for vortex_panel_wing in self.airplane.wings:

                    vortex_panel_wings_panels = np.ravel(vortex_panel_wing.panels)
                    for vortex_panel_index, vortex_panel in np.ndenumerate(vortex_panel_wings_panels):
                        normalized_induced_velocity_at_collocation_point = (
                            vortex_panel.calculate_normalized_induced_velocity(collocation_panel.collocation_point))

                        collocation_panel_normal_direction = collocation_panel.normal_direction

                        normal_normalized_induced_velocity_at_collocation_point = np.dot(
                            normalized_induced_velocity_at_collocation_point, collocation_panel_normal_direction)

                        self.aerodynamic_influence_coefficients[collocation_panel_index, vortex_panel_index] = (
                            normal_normalized_induced_velocity_at_collocation_point)

    # ToDo: Properly document this method.
    def set_up_operating_point(self):
        """

        :return:
        """

        # This calculates and updates the direction the wind is going to, in geometry axes coordinates.
        self.freestream_velocity = np.expand_dims(
            self.operating_point.calculate_freestream_velocity_geometry_axes(),
            0)

        for collocation_panel_wing in self.airplane.wings:

            collocation_panel_wings_panels = np.ravel(collocation_panel_wing.panels)
            for collocation_panel_index, collocation_panel in np.ndenumerate(collocation_panel_wings_panels):
                self.normal_directions[collocation_panel_index] = (
                    collocation_panel.normal_direction)
                self.freestream_influences[collocation_panel_index] = (
                    np.dot(self.freestream_velocity, collocation_panel.normal_direction))

    # ToDo: Properly document this method.
    def calculate_vortex_strengths(self):
        """

        :return:
        """

        self.vortex_strengths = np.linalg.solve(self.aerodynamic_influence_coefficients, -self.freestream_influences)
        for wing in self.airplane.wings:

            wing_panels = np.ravel(wing.panels)
            for panel_index, panel in np.ndenumerate(wing_panels):
                panel.ring_vortex.update_strength(self.vortex_strengths[panel_index])
                if panel.horseshoe_vortex is not None:
                    panel.horseshoe_vortex.update_strength(self.vortex_strengths[panel_index])

    # ToDo: Properly document this method.
    def calculate_solution_velocity(self, point):
        """

        :param point:
        :return:
        """

        velocity_induced_by_vortices = np.zeros(3)

        for wing in self.airplane.wings:

            wing_panels = np.ravel(wing.panels)
            for panel in wing_panels:
                velocity_induced_by_vortices += panel.calculate_induced_velocity(point)

        freestream = self.operating_point.calculate_freestream_velocity_geometry_axes()

        return velocity_induced_by_vortices + freestream

    # ToDo: Properly cite and document this method.
    def calculate_near_field_forces_and_moments(self):
        """

        :return:
        """

        airplane = self.airplane
        density = self.operating_point.density

        for wing in airplane.wings:
            panels = wing.panels
            num_chordwise_panels = wing.num_chordwise_panels
            num_spanwise_panels = wing.num_spanwise_panels
            for chordwise_location in range(num_chordwise_panels):
                for spanwise_location in range(num_spanwise_panels):
                    panel = panels[chordwise_location, spanwise_location]

                    is_right_edge = (spanwise_location + 1 == num_spanwise_panels)
                    is_leading_edge = panel.is_leading_edge
                    is_left_edge = (spanwise_location == 0)

                    if is_right_edge:
                        right_bound_vortex_strength = panel.ring_vortex.strength
                    else:
                        right_bound_vortex_strength = 0
                    if is_leading_edge:
                        front_bound_vortex_strength = panel.ring_vortex.strength
                    else:
                        front_bound_vortex_strength = (
                            panel.ring_vortex.strength
                            - panels[chordwise_location - 1, spanwise_location].ring_vortex.strength
                        )
                    if is_left_edge:
                        left_bound_vortex_strength = panel.ring_vortex.strength
                    else:
                        left_bound_vortex_strength = (
                            panel.ring_vortex.strength
                            - panels[chordwise_location, spanwise_location - 1].ring_vortex.strength
                        )

                    if right_bound_vortex_strength != 0:
                        velocity_at_right_bound_vortex_center = self.calculate_solution_velocity(
                            panel.ring_vortex.right_leg.center)
                        panel.ring_vortex.right_leg.near_field_force = (
                                density
                                * right_bound_vortex_strength
                                * np.cross(velocity_at_right_bound_vortex_center, panel.ring_vortex.right_leg.vector)
                        )
                    if front_bound_vortex_strength != 0:
                        velocity_at_front_bound_vortex_center = self.calculate_solution_velocity(
                            panel.ring_vortex.right_leg.center)
                        panel.ring_vortex.front_leg.near_field_force = (
                                density
                                * front_bound_vortex_strength
                                * np.cross(velocity_at_front_bound_vortex_center, panel.ring_vortex.front_leg.vector)
                        )
                    if left_bound_vortex_strength != 0:
                        velocity_at_left_bound_vortex_center = self.calculate_solution_velocity(
                            panel.ring_vortex.right_leg.center)
                        panel.ring_vortex.left_leg.near_field_force = (
                                density
                                * left_bound_vortex_strength
                                * np.cross(velocity_at_left_bound_vortex_center, panel.ring_vortex.left_leg.vector)
                        )

                    panel.update_force_moment_and_pressure()

    # ToDo: Properly document this method.
    def calculate_streamlines(self):
        """

        :return:
        """

        airplane = self.airplane

        num_steps = 10
        delta_time = 0.1

        for wing in airplane.wings:
            wing.streamline_points = np.zeros((num_steps + 1, wing.num_spanwise_panels, 3))
            chordwise_position = wing.num_chordwise_panels - 1

            # Increment through the wing's chordwise and spanwise positions.
            for spanwise_position in range(wing.num_spanwise_panels):

                # Pull the panel object out of the wing's list of panels.
                panel = wing.panels[chordwise_position, spanwise_position]
                seed_point = panel.back_left_vertex + 0.5 * (panel.back_right_vertex - panel.back_left_vertex)
                wing.streamline_points[0, spanwise_position, :] = seed_point
                for step in range(num_steps):
                    last_point = wing.streamline_points[step, spanwise_position, :]

                    wing.streamline_points[step + 1, spanwise_position, :] = (
                            last_point
                            + delta_time
                            * self.calculate_solution_velocity(last_point)
                    )
