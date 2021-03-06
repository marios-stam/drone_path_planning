#!/usr/bin/env python

# Author: Mark Moll
from click import echo_via_pager
from stl import mesh
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits import mplot3d
from geometry_msgs.msg import Point, PoseStamped, Quaternion, Pose
import rospy
import tf
import numpy as np
import matplotlib.pyplot as plt
from math import pi

try:
    from ompl import base as ob
    from ompl import geometric as og
except ImportError:
    # if the ompl module is not in the PYTHONPATH assume it is installed in a
    # subdirectory of the parent directory called "py-bindings."
    import sys
    from os.path import abspath, dirname, join
    sys.path.insert(
        0, join(dirname(dirname(abspath(__file__))), 'py-bindings'))
    from ompl import base as ob
    from ompl import geometric as og

try:
    from .fcl_checker import Fcl_checker
except ImportError:
    from fcl_checker import Fcl_checker

import os

print("cwd:", os.getcwd())


SHOW_VALID_STATES_CNTR = 0


class PlannerSepCollision:
    def __init__(self, env_mesh_name, robot_mesh_name) -> None:
        self.time_sum = 0
        self.states_tried = 0
        # env_mesh_name and robot_mesh_name are type of "env-scene-hole.stl"
        try:
            env_mesh = "ros_ws/src/drone_path_planning/resources/stl/{}".format(
                env_mesh_name)
            robot_mesh = "ros_ws/src/drone_path_planning/resources/stl/{}".format(
                robot_mesh_name)

            self.checker = Fcl_checker(env_mesh, robot_mesh)

            # try:
            #     checker = Fcl_checker(env_mesh, robot_mesh)
            # except:
            #     prefix = "crazyswarm/"
            #     checker = Fcl_checker(
            #         prefix+env_mesh, prefix + robot_mesh)
        except:
            print("cwd:", os.getcwd())
            env_mesh = r"/home/marios/thesis_ws/src/drone_path_planning/resources/stl/{}".format(
                env_mesh_name)
            robot_mesh = r"/home/marios/thesis_ws/src/drone_path_planning/resources/stl/{}".format(
                robot_mesh_name)

            self.checker = Fcl_checker(env_mesh, robot_mesh)

        self.space = ob.RealVectorStateSpace(4)

        # set lower and upper bounds
        self.set_bounds()

        self.ss = og.SimpleSetup(self.space)
        # set State Validity Checker function
        self.ss.setStateValidityChecker(
            ob.StateValidityCheckerFn(self.isStateValid))

        self.ss.getSpaceInformation().setStateValidityCheckingResolution(0.001)
        # set problem optimization objective
        self.set_optim_objective()

        print("Space Bounds High:", self.space.getBounds(
        ).high[0], self.space.getBounds().high[1], self.space.getBounds().high[2])
        print("Space Bounds Low:", self.space.getBounds(
        ).low[0], self.space.getBounds().low[1], self.space.getBounds().low[2])

    def set_optim_objective(self, objective_class=ob.MechanicalWorkOptimizationObjective):
        self.ss.setOptimizationObjective(
            objective_class(self.ss.getSpaceInformation()))

    def set_planner(self, planner_class=og.RRT):
        # choose planner
        planner = planner_class(self.ss.getSpaceInformation())

        self.ss.setPlanner(planner)
        self.ss.setup()

    def set_bounds(self):
        bounds = ob.RealVectorBounds(4)
        # set bounds for x, y, z , rotation
        bounds.low[0] = -2.2
        bounds.low[1] = 2.8
        bounds.low[2] = 0.5
        bounds.low[3] = -pi

        # set bounds for x, y, z, rotation
        bounds.high[0] = 2.2
        bounds.high[1] = 5.0
        bounds.high[2] = 2.5
        bounds.high[3] = pi

        # bounds.setLow(-10)
        # bounds.setHigh(10)
        self.space.setBounds(bounds)

        return bounds

    def save_path(self, file_name="path.txt"):
        # save the path
        print("Saving path to %s" % file_name)
        text_file = open(file_name, "w")
        n = text_file.write(self.path.printAsMatrix())
        text_file.close()

    def set_start_goal(self, start_pose: Pose, goal_pose: Pose, transform=False):

        # define start state
        start = ob.State(self.space)

        start[0] = start_pose.position.x
        start[1] = start_pose.position.y
        start[2] = start_pose.position.z
        start[3] = tf.transformations.euler_from_quaternion(
            [start_pose.orientation.x, start_pose.orientation.y, start_pose.orientation.z, start_pose.orientation.w])[2]

        goal = ob.State(self.space)
        goal[0] = goal_pose.position.x
        goal[1] = goal_pose.position.y
        goal[2] = goal_pose.position.z
        goal[3] = tf.transformations.euler_from_quaternion(
            [goal_pose.orientation.x, goal_pose.orientation.y, goal_pose.orientation.z, goal_pose.orientation.w])[2]

        print("start:", start)
        print("goal:", goal)

        self.ss.setStartAndGoalStates(start, goal)
        # return the start & goal states
        return start, goal

    def solve(self, timeout=15.0):
        #

        # this will automatically choose a default planner with
        # default parameters
        print(f"Solving with timeout: {timeout} sec...")
        solved = self.ss.solve(timeout)
        if solved:
            print("Found solution...")
            # try to shorten the path
            self.ss.simplifySolution()
            # print the simplified path
            path = self.ss.getSolutionPath()
            path.interpolate(50)

            self.path = path
            self.save_path()
        else:
            print("No solution found")

        print("Tried {} states --> average time: {} msec".format(self.states_tried,
              self.time_sum / self.states_tried*1000))
        return solved

    def visualize_path(self, path_file="path.txt"):
        try:
            data = np.loadtxt(path_file)
        except Exception as e:
            print("No path file found")

        fig = plt.figure()
        ax = fig.gca(projection='3d')
        ax.plot(data[:, 3], data[:, 2], data[:, 1], '.-')

        # Load the STL files and add the vectors to the plot
        env_mesh = mesh.Mesh.from_file(env_mesh_name)

        ax.add_collection3d(mplot3d.art3d.Poly3DCollection(env_mesh.vectors))

        # Auto scale to the mesh size
        scale = env_mesh.points.flatten()
        ax.auto_scale_xyz(scale, scale, scale)

        # set axes limits
        ax.set_xlim3d(-2, 5, 2.5)
        ax.set_ylim3d(-2, 5, 2.5)
        ax.set_zlim3d(-2, 5, 2.5)

        ax.set_xlabel('X axis')
        ax.set_ylabel('Y axis')
        ax.set_zlabel('Z axis')

        # printCoords(ax, data[0, 1], data[0, 2], data[0, 3])
        # printCoords(ax, data[-1, 1], data[-1, 2], data[-1, 3])

        plt.show()

    def isStateValid(self, state):
        t0 = rospy.get_time()

        pos = [state[0], state[1], state[2]]
        q = tf.transformations.quaternion_from_euler(0, 0, state[3])

        self.checker.set_robot_transform(pos, q)
        no_collision = not self.checker.check_collision()

        dt = rospy.get_time()-t0
        self.time_sum += dt
        self.states_tried += 1

        if (SHOW_VALID_STATES_CNTR and self.states_tried % 1000) == 0:
            print("Tried {} states --> average time: {} msec".format(self.states_tried,
                  self.time_sum / self.states_tried*1000), end="")
            print("\r", end="")

        return no_collision


def isBetween(x, min, max):
    return x >= min and x <= max


if __name__ == "__main__":
    # checker.visualize()
    env_mesh_name = "env-scene-hole.stl"
    robot_mesh_name = "robot-scene-triangle.stl"
    planner = PlannerSepCollision(env_mesh_name, robot_mesh_name)

    start_pos = [-4, -2, 2]
    goal_pos = [4, 2, 2]

    # start
    start_pose = PoseStamped()
    start_pose.pose.position = Point(start_pos[0], start_pos[1], start_pos[2])
    # start_pose.pose.orientation = Quaternion(-0.7071067811865475, 0, 0, 0.7071067811865476)
    start_pose.pose.orientation = Quaternion(0, 0, 0, 1)

    # goal
    goal_pose = PoseStamped()
    goal_pose.pose.position = Point(goal_pos[0], goal_pos[1], goal_pos[2])
    goal_pose.pose.orientation = Quaternion(0, 0, 0, 1)
    # goal_pose.pose.orientation = Quaternion(-0.7071067811865475, 0, 0, 0.7071067811865476)

    # if transform:
    #     start_pose = transform(start_pose)
    #     goal_pose = transform(goal_pose)

    planner.set_start_goal(start_pose.pose, goal_pose.pose)
    planner.set_planner()
    solved = planner.solve(timeout=80.0)
    if solved:
        planner.visualize_path()
