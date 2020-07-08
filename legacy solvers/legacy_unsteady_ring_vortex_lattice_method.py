""" This module contains the class definition of this package's unsteady ring vortex lattice solver.

This module contains the following classes:
    UnsteadyRingVortexLatticeMethodSolver: This is an aerodynamics solver that uses an unsteady ring vortex lattice
                                           method.

This module contains the following exceptions:
    None

This module contains the following functions:
    None
"""

import copy as copy

import numpy as np

import pterasoftware as ps


class UnsteadyRingVortexLatticeMethodSolver:
    """ This is an aerodynamics solver that uses an unsteady ring vortex lattice method.

    This class contains the following public methods:
        run: This method runs the solver on the unsteady problem.
        initialize_panel_vortices: This method calculates the locations of an airplane's bound vortex vertices, and then
                                   initializes its panels' bound vortices.
        calculate_wing_wing_influences: This method finds the matrix of wing-wing influences associated with this
                                        problem's geometry.
        calculate_freestream_wing_influences: This method finds the vector of freestream-wing influences associated with
                                              the problem at this time step.
        calculate_wake_wing_influences: This method finds the matrix of wing-wing influence coefficients associated with
                                        this airplane's geometry.
        calculate_vortex_strengths: This method solves for each panel's vortex strength.
        calculate_solution_velocity: This method finds the velocity at a given point due to the freestream and the
                                     vortices.
        calculate_velocity_influences: This method finds the velocity at a given point due to the vorticity of every
                                       vortex if their strengths were all set to 1.0 meters squared per second.
        calculate_near_field_forces_and_moments: This method finds the the forces and moments calculated from the near
                                                 field.
        calculate_streamlines: This method calculates the location of the streamlines coming off the back of the wings.
        populate_next_airplanes_wake: This method updates the next time step's airplane's wake.
        populate_next_airplanes_wake_vortex_vertices: This method populates the locations of the next airplane's wake
                                                      vortex vertices.
        populate_next_airplanes_wake_vortices: This method populates the locations of the next airplane's wake vortices.
        debug_vortices: This method prints out the current strength of the problem's vortices.
        calculate_flapping_velocity: This method gets the velocity due to flapping at a point on the panel of the
                                     current airplane based its current position, and its last position.

    This class contains the following class attributes:
        None

    Subclassing:
        This class is not meant to be subclassed.
    """

    def __init__(self, unsteady_problem):
        """ This is the initialization method.

        :param unsteady_problem: UnsteadyProblem
            This is the unsteady problem to be solved.
        """

        # Initialize this solution's attributes.
        self.num_steps = unsteady_problem.num_steps
        self.delta_time = unsteady_problem.delta_time
        self.steady_problems = unsteady_problem.steady_problems

        # Initialize attributes to hold aerodynamic data that pertains to this problem.
        self.current_step = None
        self.current_airplane = None
        self.current_operating_point = None
        self.current_freestream_velocity_geometry_axes = None
        self.current_wing_wing_influences = None
        self.current_freestream_wing_influences = None
        self.current_wake_wing_influences = None
        self.current_vortex_strengths = None
        self.streamline_points = None

    def run(self, verbose=True, prescribed_wake=True):
        """ This method runs the solver on the unsteady problem.

        :param verbose: Bool, optional
            This parameter determines if the solver prints output to the console and opens a visualization. It's default
            value is True.
        :param prescribed_wake: Bool, optional
            This parameter determines if the solver uses a prescribed wake model. If false it will use a free-wake,
            which may be more accurate but will make the solver significantly slower. The default is True.
        :return: None
        """

        # Initialize all the airplanes' panels' vortices.
        if verbose:
            print("Initializing all airplanes' panel vortices.")
        self.initialize_panel_vortices()

        # Iterate through the time steps.
        for step in range(self.num_steps):

            # Save attributes to hold the current step, airplane, and operating point.
            self.current_step = step
            self.current_airplane = self.steady_problems[self.current_step].airplane
            self.current_operating_point = self.steady_problems[
                self.current_step
            ].operating_point
            self.current_freestream_velocity_geometry_axes = (
                self.current_operating_point.calculate_freestream_velocity_geometry_axes()
            )
            if verbose:
                print(
                    "\nBeginning time step "
                    + str(self.current_step)
                    + " out of "
                    + str(self.num_steps - 1)
                    + "."
                )

            # Initialize attributes to hold aerodynamic data that pertains to this problem.
            self.current_wing_wing_influences = np.zeros(
                (self.current_airplane.num_panels, self.current_airplane.num_panels)
            )
            self.current_freestream_velocity_geometry_axes = (
                self.current_operating_point.calculate_freestream_velocity_geometry_axes()
            )
            self.current_freestream_wing_influences = np.zeros(
                self.current_airplane.num_panels
            )
            self.current_wake_wing_influences = np.zeros(
                self.current_airplane.num_panels
            )
            self.current_vortex_strengths = np.zeros(self.current_airplane.num_panels)

            # Find the matrix of wing-wing influence coefficients associated with this current_airplane's geometry.
            if verbose:
                print("Calculating the wing-wing influences.")
            self.calculate_wing_wing_influences()

            # Find the vector of freestream-wing influence coefficients associated with this problem.
            if verbose:
                print("Calculating the freestream-wing influences.")
            self.calculate_freestream_wing_influences()

            # Find the vector of wake-wing influence coefficients associated with this problem.
            if verbose:
                print("Calculating the wake-wing influences.")
            self.calculate_wake_wing_influences()

            # Solve for each panel's vortex strength.
            if verbose:
                print("Calculating vortex strengths.")
            self.calculate_vortex_strengths()

            # Solve for the near field forces and moments on each panel.
            if verbose:
                print("Calculating near field forces.")
            self.calculate_near_field_forces_and_moments()

            # Solve for the near field forces and moments on each panel.
            if verbose:
                print("Shedding wake vortices.")
            self.populate_next_airplanes_wake(prescribed_wake=prescribed_wake)

            # If the user has requested verbose output, print out the strength of all the ring vortices.
            if verbose:
                self.debug_wake_vortices()

        # Solve for the location of the streamlines coming off the back of the wings.
        if verbose:
            print("\nCalculating streamlines.")
        self.calculate_streamlines()

    def initialize_panel_vortices(self):
        """ This method calculates the locations every problem's airplane's bound vortex vertices, and then initializes
        its panels' bound vortices.

        Every panel has a ring vortex, which is a quadrangle whose front vortex leg is at the panel's quarter chord.
        The left and right vortex legs run along the panel's left and right legs. If the panel is not along the
        trailing edge, they extend backwards and meet the back vortex leg at a length of one quarter of the rear
        panel's chord back from the rear panel's front leg. Otherwise, they extend back backwards and meet the back
        vortex leg at a length of one quarter of the current panel's chord back from the current panel's back leg.

        :return: None
        """

        # Iterate through all the steady problem objects.
        for steady_problem in self.steady_problems:

            # Iterate through this problem's airplane's wings.
            for wing in steady_problem.airplane.wings:

                # Iterate through the wing's chordwise and spanwise positions.
                for chordwise_position in range(wing.num_chordwise_panels):
                    for spanwise_position in range(wing.num_spanwise_panels):

                        # Get the panel object from the wing's list of panels.
                        panel = wing.panels[chordwise_position, spanwise_position]

                        # Find the location of the panel's front left and right vortex vertices.
                        front_left_vortex_vertex = panel.front_left_vortex_vertex
                        front_right_vortex_vertex = panel.front_right_vortex_vertex

                        # Define the back left and right vortex vertices based on whether the panel is along the
                        # trailing edge or not.
                        if not panel.is_trailing_edge:
                            next_chordwise_panel = wing.panels[
                                chordwise_position + 1, spanwise_position
                            ]
                            back_left_vortex_vertex = (
                                next_chordwise_panel.front_left_vortex_vertex
                            )
                            back_right_vortex_vertex = (
                                next_chordwise_panel.front_right_vortex_vertex
                            )
                        else:
                            back_left_vortex_vertex = front_left_vortex_vertex + (
                                panel.back_left_vertex - panel.front_left_vertex
                            )
                            back_right_vortex_vertex = front_right_vortex_vertex + (
                                panel.back_right_vertex - panel.front_right_vertex
                            )

                        # Initialize the panel's ring vortex.
                        panel.ring_vortex = ps.aerodynamics.RingVortex(
                            front_right_vertex=front_right_vortex_vertex,
                            front_left_vertex=front_left_vortex_vertex,
                            back_left_vertex=back_left_vortex_vertex,
                            back_right_vertex=back_right_vortex_vertex,
                            strength=None,
                        )

    def calculate_wing_wing_influences(self):
        """ This method finds the matrix of wing-wing influence coefficients associated with this airplane's geometry.

        :return: None
        """

        # Initialize two variables to hold the global positions of the current collocation and vortex panel.
        global_collocation_panel_index = 0
        global_vortex_panel_index = 0

        # Iterate through the current_airplane's wings. This wing contains the panel with the collocation point where
        # the vortex influence is to be calculated.
        for collocation_panel_wing in self.current_airplane.wings:

            # Convert the 2D ndarray of this wing's panels into a 1D list.
            collocation_panels = np.ravel(collocation_panel_wing.panels)

            # Iterate through the list of panels with the collocation points.
            for collocation_panel in collocation_panels:

                # Iterate through the current_airplane's wings. This wing contains the panel with the vortex whose
                # influence on the collocation point is to be calculated.
                for vortex_panel_wing in self.current_airplane.wings:

                    # Convert the 2D ndarray of this wing's panels into a 1D list.
                    vortex_panels = np.ravel(vortex_panel_wing.panels)

                    # Iterate through the list of panels with the vortices.
                    for vortex_panel in vortex_panels:
                        # Calculate the velocity induced at this collocation point by this vortex if the vortex's
                        # strength was 1.
                        normalized_induced_velocity_at_collocation_point = vortex_panel.calculate_normalized_induced_velocity(
                            collocation_panel.collocation_point
                        )

                        # Find the normal direction of the panel with the collocation point.
                        collocation_panel_normal_direction = (
                            collocation_panel.normal_direction
                        )

                        # Calculate the normal component of the velocity induced at this collocation point by this
                        # vortex if the vortex's strength was 1.
                        normal_normalized_induced_velocity_at_collocation_point = np.dot(
                            normalized_induced_velocity_at_collocation_point,
                            collocation_panel_normal_direction,
                        )

                        # Add this value to the solver's aerodynamic influence coefficient matrix at the location
                        # specified by the global collocation and vortex panel indices.
                        self.current_wing_wing_influences[
                            global_collocation_panel_index, global_vortex_panel_index
                        ] = normal_normalized_induced_velocity_at_collocation_point

                        # At the next loop, we will analyze the effect of the next vortex panel on this collocation
                        # panel, so increment the global vortex panel's index.
                        global_vortex_panel_index += 1

                # At the next loop, we will analyze the effects of all the vortex panels on the next collocation panel,
                # so increment the collocation panel's global index. As we are starting over with the vortex panels, set
                # the vortex panel's global index to zero.
                global_collocation_panel_index += 1
                global_vortex_panel_index = 0

    def calculate_freestream_wing_influences(self):
        """ This method finds the vector of freestream-wing influences associated with the problem at this time step.

        Note: This contains the influence due to the freestream and due to any geometry movement relative to the
        freestream.

        :return: None
        """

        # Initialize a variable to hold the global position of the current collocation panel.
        global_collocation_panel_index = 0

        # Iterate through the current_airplane's wings.
        for collocation_panel_wing_position in range(len(self.current_airplane.wings)):

            # Get the current collocation panel wing.
            collocation_panel_wing = self.current_airplane.wings[
                collocation_panel_wing_position
            ]

            # Iterate through the chordwise and spanwise panel locations on the current collocation wing.
            for collocation_panel_chordwise_position in range(
                collocation_panel_wing.num_chordwise_panels
            ):
                for collocation_panel_spanwise_position in range(
                    collocation_panel_wing.num_spanwise_panels
                ):
                    # Get the panel at this location, and its normal direction.
                    collocation_panel = collocation_panel_wing.panels[
                        collocation_panel_chordwise_position,
                        collocation_panel_spanwise_position,
                    ]
                    collocation_panel_normal_direction = (
                        collocation_panel.normal_direction
                    )

                    # Calculate the velocity due to flapping at this point.
                    velocity_induced_by_flapping_at_collocation_point = self.calculate_flapping_velocity_on_panel(
                        wing_position=collocation_panel_wing_position,
                        panel_chordwise_position=collocation_panel_chordwise_position,
                        panel_spanwise_position=collocation_panel_spanwise_position,
                        point_name="collocation_point",
                    )

                    # Calculate the freestream influence, which is found by dotting the sum of the freestream and
                    # flapping velocity on the panel with its normal unit vector. Update the influence at the current
                    # collocation panel, as located by global index.
                    self.current_freestream_wing_influences[
                        global_collocation_panel_index
                    ] = np.dot(
                        (
                            self.current_freestream_velocity_geometry_axes
                            + velocity_induced_by_flapping_at_collocation_point
                        ),
                        collocation_panel_normal_direction,
                    )

                    # At the next loop, we will analyze the freestream influences on the next collocation panel, so
                    # increment the panel's global index.
                    global_collocation_panel_index += 1

    def calculate_wake_wing_influences(self):
        """ This method finds the vector of the wake-wing influences associated with the problem at this time step.

        :return: None
        """

        # Initialize a variable to hold the global position of the current collocation panel.
        global_collocation_panel_index = 0

        # Iterate through the wings.
        for collocation_panel_wing in self.current_airplane.wings:

            # Convert the 2D ndarray of this wing's panels into a 1D list.
            collocation_panels = np.ravel(collocation_panel_wing.panels)

            # Iterate through the list of panels with the collocation points.
            for collocation_panel in collocation_panels:

                # Get this panel's collocation point and normal direction.
                collocation_point = collocation_panel.collocation_point
                collocation_panel_normal_direction = collocation_panel.normal_direction

                # Initialize a 1D vector to hold the influence of the wake on this collocation point.
                wake_velocity = np.zeros(3)

                # Iterate through the wings with the wakes to be analyzed.
                for wake_ring_vortex_wing in self.current_airplane.wings:

                    # Convert the matrix of wake ring vortices into a 1D vector.
                    wake_ring_vortices = np.ravel(
                        wake_ring_vortex_wing.wake_ring_vortices
                    )

                    # Iterate through this wing's wake ring vortices.
                    for wake_ring_vortex in wake_ring_vortices:

                        # If the wake ring vortex exists, add the velocity it induces to the total wake velocity at
                        # this collocation point.
                        if wake_ring_vortex is not None:
                            wake_velocity += wake_ring_vortex.calculate_induced_velocity(
                                collocation_point
                            )

                # Calculate the wake influence on this collocation point and add it to the 1D vector of all the wake
                # influences on each panel's collocation point. Update the influence at the current collocation
                # panel, as located by global index.
                self.current_wake_wing_influences[
                    global_collocation_panel_index
                ] = np.dot(wake_velocity, collocation_panel_normal_direction)

                # At the next loop, we will analyze the wake influences on the next collocation panel, so
                # increment the panel's global index.
                global_collocation_panel_index += 1

    def calculate_vortex_strengths(self):
        """ This method solves for each panel's vortex strength.

        :return: None
        """

        # Solve for the strength of each panel's vortex.
        self.current_vortex_strengths = np.linalg.solve(
            self.current_wing_wing_influences,
            -self.current_wake_wing_influences
            - self.current_freestream_wing_influences,
        )

        # Initialize a variable to hold the global position of the current panel.
        global_panel_index = 0

        # Iterate through the current_airplane's wings.
        for wing in self.current_airplane.wings:

            # Convert the 2D ndarray of this wing's panels into a 1D list.
            wing_panels = np.ravel(wing.panels)

            # Iterate through this list of panels.
            for panel in wing_panels:
                # Update each panel's ring vortex strength.
                panel.ring_vortex.update_strength(
                    self.current_vortex_strengths[global_panel_index]
                )

                # At the next loop, we will update the vortex strength of the next panel, so increment the panel's
                # global index.
                global_panel_index += 1

    def calculate_solution_velocity(self, point):
        """ This method finds the velocity at a given point due to the freestream and the vortices.

        Note: The velocity this method returns does not include the velocity due to flapping. The velocity calculated by
        this method is in geometry axes.

        :param point: 1D ndarray of floats
            This is the x, y, and z coordinates of the location, in meters, where this method will solve for the
            velocity.
        :return solution_velocity: 1D ndarray of floats
            This is the x, y, and z components of the velocity, in meters per second, where this method will solve for
            the velocity.
        """

        # Initialize a vector to hold the velocity induced by the vortices.
        velocity_induced_by_vortices = np.zeros(3)

        # Iterate through the wings of the current airplane.
        for wing in self.current_airplane.wings:

            # Convert the 2D matrix of wing panels to a 1D vector.
            wing_panels = np.ravel(wing.panels)

            # Iterate through this wing's panels, and add the the induced velocity at this panel to the total velocity
            # induced by vortices.
            for panel in wing_panels:
                velocity_induced_by_vortices += panel.calculate_induced_velocity(point)

            # Convert the 2D matrix of wake ring vortices to a 1D vector.
            wake_ring_vortices = np.ravel(wing.wake_ring_vortices)

            # Iterate through this wing's wake's vortices, and add the the induced velocity at this panel to the
            # total velocity induced by vortices.
            for wake_ring_vortex in wake_ring_vortices:
                if wake_ring_vortex is not None:
                    velocity_induced_by_vortices += wake_ring_vortex.calculate_induced_velocity(
                        point
                    )

        # Add the velocity induced by the vortices to the freestream velocity. Return the sum.
        solution_velocity = (
            velocity_induced_by_vortices
            + self.current_freestream_velocity_geometry_axes
        )
        return solution_velocity

    def calculate_near_field_forces_and_moments(self):
        """ This method finds the the forces and moments calculated from the near field.

        Citation:
            This method uses logic described on pages 9-11 of "Modeling of aerodynamic forces in flapping flight with
            the Unsteady Vortex Lattice Method" by Thomas Lambert.

        Note: The forces and moments calculated are in geometry axes. The moment is about the current_airplane's
        reference point, which should be at the center of gravity. The units are Newtons and Newton-meters.

        :return: None
        """

        # Initialize variables to hold the total near field force and moment on this airplane in geometry axes.
        total_near_field_force_geometry_axes = np.zeros(3)
        total_near_field_moment_geometry_axes = np.zeros(3)

        # If the this isn't the first step, set the last step to one less than the current step. If this is the first
        # step, then set the last step to the first step.
        if self.current_step > 0:
            last_step = self.current_step - 1
        else:
            last_step = self.current_step

        # Get the last airplane object.
        last_airplane = self.steady_problems[last_step].airplane

        # Iterate through the current airplane's wings.
        for wing_num in range(len(self.current_airplane.wings)):

            # Get the wing, the current matrix of panels, and last wing, and the last matrix of panels.
            wing = self.current_airplane.wings[wing_num]
            last_wing = last_airplane.wings[wing_num]
            panels = wing.panels
            last_panels = last_wing.panels

            # Iterate through the chordwise and spanwise locations of the panels.
            for chordwise_location in range(wing.num_chordwise_panels):
                for spanwise_location in range(wing.num_spanwise_panels):

                    # Ge the current and last panel objects.
                    panel = panels[chordwise_location, spanwise_location]
                    last_panel = last_panels[chordwise_location, spanwise_location]

                    # Determine if this panel is on the right edge, leading edge, trailing edge, and/or the left edge of
                    # the wing.
                    is_right_edge = spanwise_location + 1 == wing.num_spanwise_panels
                    is_leading_edge = panel.is_leading_edge
                    is_left_edge = spanwise_location == 0

                    # If this panel is on the right edge, set the right bound vortex strength to the panel's ring
                    # vortex's strength. Otherwise set the strength to zero.
                    if is_right_edge:
                        right_bound_vortex_strength = panel.ring_vortex.strength
                    else:
                        right_bound_vortex_strength = 0

                    # If this panel is on the leading edge, set the leading bound vortex strength this panel's vortex
                    # strength. Otherwise set the strength to the difference between this panel's vortex strength and
                    # the forward panel's vortex strength.
                    if is_leading_edge:
                        front_bound_vortex_strength = panel.ring_vortex.strength
                    else:
                        front_bound_vortex_strength = (
                            panel.ring_vortex.strength
                            - panels[
                                chordwise_location - 1, spanwise_location
                            ].ring_vortex.strength
                        )

                    # If this panel is on the left edge, set the left bound vortex strength this panel's vortex
                    # strength. Otherwise set the strength to the difference between this panel's vortex strength and
                    # the leftward panel's vortex strength.
                    if is_left_edge:
                        left_bound_vortex_strength = panel.ring_vortex.strength
                    else:
                        left_bound_vortex_strength = (
                            panel.ring_vortex.strength
                            - panels[
                                chordwise_location, spanwise_location - 1
                            ].ring_vortex.strength
                        )

                    # Initialize variables to hold the panel's near field force and moment on this airplane in geometry
                    # axes.
                    panel.near_field_force_geometry_axes = np.zeros(3)
                    panel.near_field_moment_geometry_axes = np.zeros(3)

                    if right_bound_vortex_strength != 0:
                        # If the right bound vortex strength isn't zero, calculate the velocity due to the freestream,
                        # the problem's vortices, and the flapping at the center of the right leg center.
                        velocity_at_right_bound_vortex_center = self.calculate_solution_velocity(
                            panel.ring_vortex.right_leg.center
                        )
                        velocity_at_right_bound_vortex_center += self.calculate_flapping_velocity_on_panel(
                            wing_position=wing_num,
                            panel_chordwise_position=chordwise_location,
                            panel_spanwise_position=spanwise_location,
                            point_name="ring_vortex.right_leg.center",
                        )

                        # Using the Kutta-Joukowski theorem, calculate the force on this leg.
                        right_bound_vortex_force_in_geometry_axes = (
                            self.current_operating_point.density
                            * right_bound_vortex_strength
                            * np.cross(
                                velocity_at_right_bound_vortex_center,
                                panel.ring_vortex.right_leg.vector,
                            )
                        )

                        # Update the force and the moment on this panel.
                        panel.near_field_force_geometry_axes += (
                            right_bound_vortex_force_in_geometry_axes
                        )
                        panel.near_field_moment_geometry_axes += np.cross(
                            panel.ring_vortex.right_leg.center
                            - self.current_airplane.xyz_ref,
                            right_bound_vortex_force_in_geometry_axes,
                        )

                    if front_bound_vortex_strength != 0:
                        # If the front bound vortex strength isn't zero, calculate the velocity due to the freestream,
                        # the problem's vortices, and the flapping at the center of the front leg center.
                        velocity_at_front_bound_vortex_center = self.calculate_solution_velocity(
                            panel.ring_vortex.front_leg.center
                        )
                        velocity_at_front_bound_vortex_center += self.calculate_flapping_velocity_on_panel(
                            wing_position=wing_num,
                            panel_chordwise_position=chordwise_location,
                            panel_spanwise_position=spanwise_location,
                            point_name="ring_vortex.front_leg.center",
                        )

                        # Using the Kutta-Joukowski theorem, calculate the force on this leg.
                        front_bound_vortex_force_in_geometry_axes = (
                            self.current_operating_point.density
                            * front_bound_vortex_strength
                            * np.cross(
                                velocity_at_front_bound_vortex_center,
                                panel.ring_vortex.front_leg.vector,
                            )
                        )

                        # Update the force and the moment on this panel.
                        panel.near_field_force_geometry_axes += (
                            front_bound_vortex_force_in_geometry_axes
                        )
                        panel.near_field_moment_geometry_axes += np.cross(
                            panel.ring_vortex.front_leg.center
                            - self.current_airplane.xyz_ref,
                            front_bound_vortex_force_in_geometry_axes,
                        )

                    if left_bound_vortex_strength != 0:
                        # If the left bound vortex strength isn't zero, calculate the velocity due to the freestream,
                        # the problem's vortices, and the flapping at the center of the left leg center.
                        velocity_at_left_bound_vortex_center = self.calculate_solution_velocity(
                            panel.ring_vortex.left_leg.center
                        )
                        velocity_at_left_bound_vortex_center += self.calculate_flapping_velocity_on_panel(
                            wing_position=wing_num,
                            panel_chordwise_position=chordwise_location,
                            panel_spanwise_position=spanwise_location,
                            point_name="ring_vortex.left_leg.center",
                        )

                        # Using the Kutta-Joukowski theorem, calculate the force on this leg.
                        left_bound_vortex_force_in_geometry_axes = (
                            self.current_operating_point.density
                            * left_bound_vortex_strength
                            * np.cross(
                                velocity_at_left_bound_vortex_center,
                                panel.ring_vortex.left_leg.vector,
                            )
                        )

                        # Update the force and the moment on this panel.
                        panel.near_field_force_geometry_axes += (
                            left_bound_vortex_force_in_geometry_axes
                        )
                        panel.near_field_moment_geometry_axes += np.cross(
                            panel.ring_vortex.left_leg.center
                            - self.current_airplane.xyz_ref,
                            left_bound_vortex_force_in_geometry_axes,
                        )

                    # Calculate the unsteady component of the force on this panel.
                    unsteady_force_geometry_axes = (
                        self.current_operating_point.density
                        * (panel.ring_vortex.strength - last_panel.ring_vortex.strength)
                        * panel.area
                        * panel.normal_direction
                    )

                    # Add the unsteady component of the force and moment on this panel to the total near field force and
                    # moment on this panel.
                    panel.near_field_force_geometry_axes += unsteady_force_geometry_axes
                    panel.near_field_moment_geometry_axes += np.cross(
                        panel.ring_vortex.center - self.current_airplane.xyz_ref,
                        unsteady_force_geometry_axes,
                    )
                    panel.update_pressure()

                    # Add the near field force and moment on this panel to the total near field force and moment on the
                    # current airplane.
                    total_near_field_force_geometry_axes += (
                        panel.near_field_force_geometry_axes
                    )
                    total_near_field_moment_geometry_axes += (
                        panel.near_field_moment_geometry_axes
                    )

        # Calculate the total near field force and moment on the current airplane in wind axes.
        self.current_airplane.total_near_field_force_wind_axes = (
            np.transpose(
                self.current_operating_point.calculate_rotation_matrix_wind_axes_to_geometry_axes()
            )
            @ total_near_field_force_geometry_axes
        )
        self.current_airplane.total_near_field_moment_wind_axes = (
            np.transpose(
                self.current_operating_point.calculate_rotation_matrix_wind_axes_to_geometry_axes()
            )
            @ total_near_field_moment_geometry_axes
        )

        # Calculate the force and moment coefficients of the current airplane.
        CDi = (
            -self.current_airplane.total_near_field_force_wind_axes[0]
            / self.current_operating_point.calculate_dynamic_pressure()
            / self.current_airplane.s_ref
        )
        CY = (
            self.current_airplane.total_near_field_force_wind_axes[1]
            / self.current_operating_point.calculate_dynamic_pressure()
            / self.current_airplane.s_ref
        )
        CL = (
            -self.current_airplane.total_near_field_force_wind_axes[2]
            / self.current_operating_point.calculate_dynamic_pressure()
            / self.current_airplane.s_ref
        )
        Cl = (
            self.current_airplane.total_near_field_moment_wind_axes[0]
            / self.current_operating_point.calculate_dynamic_pressure()
            / self.current_airplane.s_ref
            / self.current_airplane.b_ref
        )
        Cm = (
            self.current_airplane.total_near_field_moment_wind_axes[1]
            / self.current_operating_point.calculate_dynamic_pressure()
            / self.current_airplane.s_ref
            / self.current_airplane.c_ref
        )
        Cn = (
            self.current_airplane.total_near_field_moment_wind_axes[2]
            / self.current_operating_point.calculate_dynamic_pressure()
            / self.current_airplane.s_ref
            / self.current_airplane.b_ref
        )

        # Update the force and moment coefficients of the current airplane.
        self.current_airplane.total_near_field_force_coefficients_wind_axes = np.array(
            [CDi, CY, CL]
        )
        self.current_airplane.total_near_field_moment_coefficients_wind_axes = np.array(
            [Cl, Cm, Cn]
        )

    def calculate_streamlines(self, streamline_num_steps=10, streamline_delta_time=0.1):
        """ This method calculates the location of the streamlines coming off the back of the wings.

        :param streamline_num_steps: int, optional
            This variable is the number of time steps the streamline solver will analyze. Its default value is 10.
        :param streamline_delta_time: float, optional
            This variable is the amount of time, in seconds, between each streamline time step. Its default value is 0.1
            seconds.
        :return: None
        """

        # Initialize the streamline points attribute using the number of steps in this simulation.
        self.streamline_points = np.empty((streamline_num_steps + 1, 0, 3))

        # Get the current airplane.
        airplane = self.current_airplane

        # Iterate through the current airplane's wings.
        for wing in airplane.wings:

            # Initialize an array to hold the locations of all the streamline points.
            wing.streamline_points = np.zeros(
                (streamline_num_steps + 1, wing.num_spanwise_panels, 3)
            )

            # Set the chordwise position to be at the trailing edge.
            chordwise_position = wing.num_chordwise_panels - 1

            # Increment through the wing's spanwise positions at the trailing edge.
            for spanwise_position in range(wing.num_spanwise_panels):

                # Pull the panel object out of the wing's list of panels.
                panel = wing.panels[chordwise_position, spanwise_position]

                # Calculate the location of the seed point at this panel. It should be a bit behind the center of the
                # ring vortex's back leg. "Behind" refers to the direction the flow is moving.
                seed_point = (
                    panel.ring_vortex.back_leg.center
                    + self.current_freestream_velocity_geometry_axes
                    * self.delta_time
                    * 0.25
                )

                # Add the seed point to the first row of the wing's streamline point matrix.
                wing.streamline_points[0, spanwise_position, :] = seed_point

                # Iterate through the number of streamline steps.
                for step in range(streamline_num_steps):
                    # Pull this panel's previous streamline point.
                    last_point = wing.streamline_points[step, spanwise_position, :]

                    # Find the new streamline point's position and add it to the streamline point matrix.
                    wing.streamline_points[step + 1, spanwise_position, :] = (
                        last_point
                        + streamline_delta_time
                        * self.calculate_solution_velocity(last_point)
                    )

            # Stack the current wing's streamline point matrix on to the solver's streamline point matrix.
            self.streamline_points = np.hstack(
                (self.streamline_points, wing.streamline_points)
            )

    def populate_next_airplanes_wake(self, prescribed_wake=True):
        """ This method updates the next time step's airplane's wake.

        :param prescribed_wake: Bool, optional
            This parameter determines if the solver uses a prescribed wake model. If false it will use a free-wake,
            which may be more accurate but will make the solver significantly slower. The default is True.

        :return: None
        """

        # Populate the locations of the next airplane's wake's vortex vertices:
        self.populate_next_airplanes_wake_vortex_vertices(
            prescribed_wake=prescribed_wake
        )

        # Populate the locations of the next airplane's wake vortices.
        self.populate_next_airplanes_wake_vortices()

    def populate_next_airplanes_wake_vortex_vertices(self, prescribed_wake=True):
        """ This method populates the locations of the next airplane's wake vortex vertices.

        :param prescribed_wake: Bool, optional
            This parameter determines if the solver uses a prescribed wake model. If false it will use a free-wake,
            which may be more accurate but will make the solver significantly slower. The default is True.
        :return: None
        """

        # Check if this is not the last step.
        if self.current_step < self.num_steps - 1:

            # Get the next airplane object and the current airplane's number of wings.
            next_airplane = self.steady_problems[self.current_step + 1].airplane
            num_wings = len(self.current_airplane.wings)

            # Iterate through the wing positions.
            for wing_num in range(num_wings):

                # Get the wing objects at this position from the current and the next airplane.
                this_wing = self.current_airplane.wings[wing_num]
                next_wing = next_airplane.wings[wing_num]

                # Check if this is the first step.
                if self.current_step == 0:

                    # Get the current wing's number of chordwise and spanwise panels.
                    num_spanwise_panels = this_wing.num_spanwise_panels
                    num_chordwise_panels = this_wing.num_chordwise_panels

                    # Set the chordwise position to be at the trailing edge.
                    chordwise_position = num_chordwise_panels - 1

                    # Initialize a matrix to hold the vertices of the new row of wake ring vortices.
                    first_row_of_wake_ring_vortex_vertices = np.zeros(
                        (1, num_spanwise_panels + 1, 3)
                    )

                    # Iterate through the spanwise panel positions.
                    for spanwise_position in range(num_spanwise_panels):

                        # Get the next wing's panel object at this location.
                        next_panel = next_wing.panels[
                            chordwise_position, spanwise_position
                        ]

                        # The position of the next front left wake ring vortex vertex is the next panel's ring vortex's
                        # back left vertex.
                        next_front_left_vertex = next_panel.ring_vortex.back_left_vertex

                        # Add this to the new row of wake ring vortex vertices.
                        first_row_of_wake_ring_vortex_vertices[
                            0, spanwise_position
                        ] = next_front_left_vertex

                        # Check if this panel is on the right edge of the wing.
                        if spanwise_position == (num_spanwise_panels - 1):
                            # The position of the next front right wake ring vortex vertex is the next panel's ring
                            # vortex's back right vertex.
                            next_front_right_vertex = (
                                next_panel.ring_vortex.back_right_vertex
                            )

                            # Add this to the new row of wake ring vortex vertices.
                            first_row_of_wake_ring_vortex_vertices[
                                0, spanwise_position + 1
                            ] = next_front_right_vertex

                    # Set the next wing's matrix of wake ring vortex vertices to a copy of the row of new wake ring
                    # vortex vertices. This is correct because this is the first time step.
                    next_wing.wake_ring_vortex_vertices = np.copy(
                        first_row_of_wake_ring_vortex_vertices
                    )

                    # Initialize variables to hold the number of spanwise vertices.
                    num_spanwise_vertices = num_spanwise_panels + 1

                    # Initialize a new matrix to hold the second row of wake ring vortex vertices.
                    second_row_of_wake_ring_vortex_vertices = np.zeros(
                        (1, num_spanwise_panels + 1, 3)
                    )

                    # Iterate through the spanwise vertex positions.
                    for spanwise_vertex_position in range(num_spanwise_vertices):

                        # Get the corresponding vertex from the first row.
                        wake_ring_vortex_vertex = next_wing.wake_ring_vortex_vertices[
                            0, spanwise_vertex_position
                        ]

                        if prescribed_wake:

                            # If the wake is prescribed, set the velocity at this vertex to the freestream velocity.
                            velocity_at_first_row_wake_ring_vortex_vertex = (
                                self.current_freestream_velocity_geometry_axes
                            )
                        else:

                            # If the wake is not prescribed, set the velocity at this vertex to the solution velocity at
                            # this point.
                            velocity_at_first_row_wake_ring_vortex_vertex = self.calculate_solution_velocity(
                                wake_ring_vortex_vertex
                            )

                        # Update the second row with the interpolated position of the first vertex.
                        second_row_of_wake_ring_vortex_vertices[
                            0, spanwise_vertex_position
                        ] = (
                            wake_ring_vortex_vertex
                            + velocity_at_first_row_wake_ring_vortex_vertex
                            * self.delta_time
                        )

                    # Update the wing's wake ring vortex vertex matrix by vertically stacking the second row below it.
                    next_wing.wake_ring_vortex_vertices = np.vstack(
                        (
                            next_wing.wake_ring_vortex_vertices,
                            second_row_of_wake_ring_vortex_vertices,
                        )
                    )

                # If this isn't the first step, then do this.
                else:

                    # Set the next wing's wake ring vortex vertex matrix to a copy of this wing's wake ring vortex
                    # vertex matrix.
                    next_wing.wake_ring_vortex_vertices = np.copy(
                        this_wing.wake_ring_vortex_vertices
                    )

                    # Get the number of chordwise and spanwise vertices.
                    num_chordwise_vertices = next_wing.wake_ring_vortex_vertices.shape[
                        0
                    ]
                    num_spanwise_vertices = next_wing.wake_ring_vortex_vertices.shape[1]

                    # Iterate through the chordwise and spanwise vertex positions.
                    for chordwise_vertex_position in range(num_chordwise_vertices):
                        for spanwise_vertex_position in range(num_spanwise_vertices):

                            # Get the wake ring vortex vertex at this position.
                            wake_ring_vortex_vertex = next_wing.wake_ring_vortex_vertices[
                                chordwise_vertex_position, spanwise_vertex_position
                            ]

                            if prescribed_wake:

                                # If the wake is prescribed, set the velocity at this vertex to the freestream velocity.
                                velocity_at_first_row_wake_vortex_vertex = (
                                    self.current_freestream_velocity_geometry_axes
                                )
                            else:

                                # If the wake is not prescribed, set the velocity at this vertex to the solution
                                # velocity at this point.
                                velocity_at_first_row_wake_vortex_vertex = self.calculate_solution_velocity(
                                    wake_ring_vortex_vertex
                                )

                            # Update the vertex at this point with its interpolated position.
                            next_wing.wake_ring_vortex_vertices[
                                chordwise_vertex_position, spanwise_vertex_position
                            ] += (
                                velocity_at_first_row_wake_vortex_vertex
                                * self.delta_time
                            )

                    # Set the chordwise position to the trailing edge.
                    chordwise_position = this_wing.num_chordwise_panels - 1

                    # Initialize a new matrix to hold the new first row of wake ring vortex vertices.
                    first_row_of_wake_ring_vortex_vertices = np.empty(
                        (1, this_wing.num_spanwise_panels + 1, 3)
                    )

                    # Iterate spanwise through the trailing edge panels.
                    for spanwise_position in range(this_wing.num_spanwise_panels):

                        # Get the panel object at this location on the next airplane's wing object.
                        next_panel = next_wing.panels[
                            chordwise_position, spanwise_position
                        ]

                        # Add the panel object's back left ring vortex vertex to the matrix of new wake ring vortex
                        # vertices.
                        first_row_of_wake_ring_vortex_vertices[
                            0, spanwise_position
                        ] = next_panel.ring_vortex.back_left_vertex

                        if spanwise_position == (this_wing.num_spanwise_panels - 1):
                            # If the panel object is at the right edge of the wing, add its back right ring vortex
                            # vertex to the matrix of new wake ring vortex vertices.
                            first_row_of_wake_ring_vortex_vertices[
                                0, spanwise_position + 1
                            ] = next_panel.ring_vortex.back_right_vertex

                    # Stack the new first row of wake ring vortex vertices above the wing's matrix of wake ring vortex
                    # vertices.
                    next_wing.wake_ring_vortex_vertices = np.vstack(
                        (
                            first_row_of_wake_ring_vortex_vertices,
                            next_wing.wake_ring_vortex_vertices,
                        )
                    )

    def populate_next_airplanes_wake_vortices(self):
        """ This method populates the locations of the next airplane's wake vortices.

        :return: None
        """

        # Create a copy of the current airplane.
        current_airplane_copy = copy.deepcopy(self.current_airplane)

        # Check if the current step is not the last step.
        if self.current_step < self.num_steps - 1:

            # Get the next airplane object.
            next_airplane = self.steady_problems[self.current_step + 1].airplane

            # Iterate through the copy of the current airplane's wing positions.
            for wing_num in range(len(current_airplane_copy.wings)):

                # Get the current airplane copy's wing, and the next airplane's wing at this location.
                this_wing_copy = current_airplane_copy.wings[wing_num]
                next_wing = next_airplane.wings[wing_num]

                # Get the next wing's matrix of wake ring vortex vertices.
                next_wing_wake_ring_vortex_vertices = (
                    next_wing.wake_ring_vortex_vertices
                )

                # Get the wake ring vortices from the this wing copy object.
                this_wing_wake_ring_vortices_copy = this_wing_copy.wake_ring_vortices

                # Find the number of chordwise and spanwise vertices in the next wing's matrix of wake ring vortex
                # vertices.
                num_chordwise_vertices = next_wing_wake_ring_vortex_vertices.shape[0]
                num_spanwise_vertices = next_wing_wake_ring_vortex_vertices.shape[1]

                # Initialize a new matrix to hold the new row of wake ring vortices.
                new_row_of_wake_ring_vortices = np.empty(
                    (1, num_spanwise_vertices - 1), dtype=object
                )

                # Stack the new matrix on top of the copy of this wing's matrix and assign it to the next wing.
                next_wing.wake_ring_vortices = np.vstack(
                    (new_row_of_wake_ring_vortices, this_wing_wake_ring_vortices_copy)
                )

                # Iterate through the vertex positions.
                for chordwise_vertex_position in range(num_chordwise_vertices):
                    for spanwise_vertex_position in range(num_spanwise_vertices):

                        # Set booleans to determine if this vertex is on the right and/or trailing edge of the wake.
                        has_right_vertex = (
                            spanwise_vertex_position + 1
                        ) < num_spanwise_vertices
                        has_back_vertex = (
                            chordwise_vertex_position + 1
                        ) < num_chordwise_vertices

                        if has_right_vertex and has_back_vertex:

                            # If this position is not on the right or trailing edge of the wake, get the four vertices
                            # that will be associated with the corresponding ring vortex at this position.
                            front_left_vertex = next_wing_wake_ring_vortex_vertices[
                                chordwise_vertex_position, spanwise_vertex_position
                            ]
                            front_right_vertex = next_wing_wake_ring_vortex_vertices[
                                chordwise_vertex_position, spanwise_vertex_position + 1
                            ]
                            back_left_vertex = next_wing_wake_ring_vortex_vertices[
                                chordwise_vertex_position + 1, spanwise_vertex_position
                            ]
                            back_right_vertex = next_wing_wake_ring_vortex_vertices[
                                chordwise_vertex_position + 1,
                                spanwise_vertex_position + 1,
                            ]

                            if chordwise_vertex_position > 0:
                                # If this is isn't the front of the wake, update the position of the ring vortex at this
                                # location.
                                next_wing.wake_ring_vortices[
                                    chordwise_vertex_position, spanwise_vertex_position
                                ].update_position(
                                    front_left_vertex=front_left_vertex,
                                    front_right_vertex=front_right_vertex,
                                    back_left_vertex=back_left_vertex,
                                    back_right_vertex=back_right_vertex,
                                )

                            if chordwise_vertex_position == 0:
                                # If this is the front of the wake, get the vortex strength from the wing panel's ring
                                # vortex direction in front of it.
                                this_strength_copy = this_wing_copy.panels[
                                    this_wing_copy.num_chordwise_panels - 1,
                                    spanwise_vertex_position,
                                ].ring_vortex.strength

                                # Then, make a new ring vortex at this location, with the panel's ring vortex's
                                # strength, and add it to the matrix of ring vortices.
                                next_wing.wake_ring_vortices[
                                    chordwise_vertex_position, spanwise_vertex_position
                                ] = ps.aerodynamics.RingVortex(
                                    front_left_vertex=front_left_vertex,
                                    front_right_vertex=front_right_vertex,
                                    back_left_vertex=back_left_vertex,
                                    back_right_vertex=back_right_vertex,
                                    strength=this_strength_copy,
                                )

    def debug_wake_vortices(self):
        """ This method prints out the current strength of the problem's vortices.

        :return: None
        """

        # Iterate through the airplane's wings.
        for wing in self.current_airplane.wings:

            print("\nWing Vortex Strengths: ")
            print("\n\tPanel Vortex Strengths:\n")

            # Iterate through the wing's panel positions.
            for chordwise_position in range(wing.num_chordwise_panels):
                for spanwise_position in range(wing.num_spanwise_panels):
                    # Get the panel at this position, its ring vortex, and its ring vortex's strength.
                    panel = wing.panels[chordwise_position, spanwise_position]
                    ring_vortex = panel.ring_vortex
                    strength = ring_vortex.strength

                    # Print out the strength.
                    print("\t\t" + str(round(strength, 2)), end="\t")
                print()
            print("\n\tWake Vortex Strengths:\n")

            # Iterate through the wing's wake vortex positions.
            for chordwise_position in range(wing.wake_ring_vortices.shape[0]):
                for spanwise_position in range(wing.wake_ring_vortices.shape[1]):
                    # Get the wake vortex at this position, and its strength.
                    ring_vortex = wing.wake_ring_vortices[
                        chordwise_position, spanwise_position
                    ]

                    # Print out the strength.
                    strength = ring_vortex.strength
                    print("\t\t" + str(round(strength, 2)), end="\t")
                print()
        print()

    def calculate_flapping_velocity_on_panel(
        self,
        wing_position,
        panel_chordwise_position,
        panel_spanwise_position,
        point_name,
    ):
        """ This method gets the velocity due to flapping at a point on the panel of the current airplane based its
        current position, and its last position.

        :param wing_position: int
            This is the position of the panel's wing in the current_airplane's list of wings.
        :param panel_chordwise_position: int
            This is the chordwise position of the panel in the wing's ndarray of panels.
        :param panel_spanwise_position: int
            This is the spanwise position of the panel in the wing's ndarray of panels.
        :param point_name: string
            This is the name of the point at which to find the velocity due to flapping. It should be the name of one of
            the point attributes of this panel (i.e. "ring_vortex.left_leg.center", "collocation_point", etc.)
        :return flapping_velocity: 1D ndarray
            This is the flapping velocity at the current time current_step at the given point. It is a (,3) ndarray with
            units of meters per second.
        """

        # If this is the first time current_step, there is no previous geometry, so the flapping velocity is (0, 0, 0)
        # meters per second.
        if self.current_step < 1:
            flapping_velocity = np.zeros(3)
            return flapping_velocity

        # Find the last current_airplane.
        last_airplane = self.steady_problems[self.current_step - 1].airplane

        # Find the current, and the last wing.
        wing = self.current_airplane.wings[wing_position]
        last_wing = last_airplane.wings[wing_position]

        # Find the current, and the last panel.
        parent = wing.panels[panel_chordwise_position, panel_spanwise_position]
        last_parent = last_wing.panels[
            panel_chordwise_position, panel_spanwise_position
        ]

        # Split the point name at the periods. Now it is a list of the nested objects within the panels.
        sub_names = point_name.split(".")

        # Initialize the two variables to hold the objects nested one level down below the panels.
        sub = None
        last_sub = None

        # Iterate through the list of the names of the nested objects.
        for sub_name in sub_names:

            # Try getting the attributes of the of the parent via the sub name.
            try:
                # Set sub and last_sub to the attributes of the parent and last_parent.
                sub = parent.__getattribute__(sub_name)
                last_sub = last_parent.__getattribute__(sub_name)

                # Set the new parent and the last_parent to the sub and last_sub.
                parent = sub
                last_parent = last_sub

            # Catch attribute errors and display an error message.
            except AttributeError:
                raise Exception(
                    "The panel doesn't have an attribute that matches your request!"
                )

        # Set the position and the last position to the latest values of sub and last_sub.
        position = sub
        last_position = last_sub

        # Calculate and return the flapping velocity.
        flapping_velocity = (position - last_position) / self.delta_time
        return flapping_velocity
