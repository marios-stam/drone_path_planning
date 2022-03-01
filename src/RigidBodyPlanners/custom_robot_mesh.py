import sys
from .fcl_checker import Fcl_mesh
from stl import mesh
import numpy as np
import fcl


class Custom_robot_mesh():
    def __init__(self, drones_distance, theta, L, catenary_lowest_function, mesh_type=None) -> None:
        self.catenary_lowest_function = catenary_lowest_function

        if mesh_type == None:
            print("mesh_type is None")
            sys.exit()
        elif mesh_type.lower() == "stl":
            self.MESH_TYPE = mesh.Mesh
        else:
            self.MESH_TYPE = Fcl_mesh

        self.create_custom_robot(drones_distance, theta, L)

    def drones_formation_2_triangle_points(self, drones_distance, theta):
        """
            This function gets the distnace between the 2 drones and the angle they form
            with the horizontal plane. It deeems a circle with radius equal to the distance/2
            and calculates the points of the triangle.
        """

        # get the distance between the 2 drones
        r = drones_distance/2
        y_offset = 1
        # get the points of the triangle
        self.p0 = np.array([r * np.cos(theta),  y_offset + r * np.sin(theta)])
        self.p1 = np.array([-r * np.cos(theta), y_offset + -r * np.sin(theta)])

        # print(np.linalg.norm(p0 - p1))

        return self.p0, self.p1

    def get_triangle_3D_points(p0, p1, p2):
        # Created a matrix with all the vertices needed for the 3D triangle
        thickness = 0.3  # thickness of the triangle ,maybe should be a parameter
        offset = 1  # TODO: makes this 0 (used for comapring with thhe old one)

        verts = np.zeros((6, 3))

        verts[0, :] = [p0[0],  offset + thickness/2, p0[1]]
        verts[1, :] = [p1[0],  offset + thickness/2, p1[1]]
        verts[2, :] = [p2[0],  offset + thickness/2, p2[1]]
        verts[3, :] = [p0[0],  offset + -thickness/2, p0[1]]
        verts[4, :] = [p1[0],  offset + -thickness/2, p1[1]]
        verts[5, :] = [p2[0],  offset + -thickness/2, p2[1]]

        return verts

    def get_tris():
        # manual triangluation of the rigid body
        tris = np.zeros((8, 3), dtype=int)
        tris[0, :] = [0, 1, 2]
        tris[1, :] = [3, 4, 5]
        tris[2, :] = [0, 1, 4]
        tris[3, :] = [0, 3, 4]
        tris[4, :] = [0, 2, 3]
        tris[5, :] = [2, 3, 5]
        tris[6, :] = [1, 2, 4]
        tris[7, :] = [2, 4, 5]

        return tris

    def create_3D_triangle_stl(p0, p1, p2, custom_filename):
        # create mesh of stl.mesh.Mesh type
        verts = Custom_robot_mesh.get_triangle_3D_points(p0, p1, p2)
        tris = Custom_robot_mesh.get_tris()

        num_triangles = tris.shape[0]
        data = np.zeros(num_triangles, dtype=mesh.Mesh.dtype)

        for i, tr in enumerate(tris):
            data["vectors"][i] = np.array(
                [verts[tr[0]], verts[tr[1]], verts[tr[2]]])

        m = mesh.Mesh(data)
        m.save(custom_filename)
        print("Saved mesh to: ", custom_filename)
        return m

    def create_3D_triangle_fcl_mesh(p0, p1, p2):
        # create mesh of Fcl_mesh type
        verts = Custom_robot_mesh.get_triangle_3D_points(p0, p1, p2)
        tris = Custom_robot_mesh.get_tris()

        m = Fcl_mesh()
        m.verts = verts
        m.tris = tris
        m.create_fcl_mesh()

        return m

    def get_triangle_2D_points(self, drones_distance, theta, L) -> mesh.Mesh:
        """
        This function generated a 3D rigid trinagle body suitable for path planning of the drone swarm
        theta : represents the angle that is formed between the line connecting the drones and the horizontal plane
        """
        # Get first 2 points based on drones distance and theta
        p0, p1 = self.drones_formation_2_triangle_points(
            drones_distance, theta)
        p0, p1 = [p0[0], p0[1], 0], [p1[0], p1[1], 0]

        # Set the lowest point of the catenary formed by the 2 previous points
        # as the 3rd point of the catenary

        lowest_point = self.catenary_lowest_function(p0, p1, L).lowest_point
        lowest_point = [lowest_point[0], lowest_point[2]]

        return p0, p1, lowest_point

    def create_custom_robot(self, drones_distance, theta, L) -> mesh.Mesh:
        p0, p1, lowest_point = self.get_triangle_2D_points(
            drones_distance, theta, L)

        if self.MESH_TYPE == mesh.Mesh:
            self.mesh = Custom_robot_mesh.create_3D_triangle_stl(
                p0, p1, lowest_point, "custom_triangle_robot.stl")

        elif self.MESH_TYPE == Fcl_mesh:
            self.mesh = Custom_robot_mesh.create_3D_triangle_fcl_mesh(
                p0, p1, lowest_point)
        else:
            print("mesh_type is not one of the expected ones...")
            sys.exit()

        return self.mesh

    def update_verts(self, drones_distance, theta, L):
        p0, p1, lowest_point = self.get_triangle_2D_points(
            drones_distance, theta, L)

        verts = Custom_robot_mesh.get_triangle_3D_points(p0, p1, lowest_point)

        return verts

    def update_mesh_fcl_mesh(self, drones_distance, theta, L):
        # verts = self.update_verts(drones_distance, theta, L)

        # this one is not working on python-fcl (doesn't have the .begin_update function)
        # self.mesh.update_vertices(verts)

        # so I end up making a new mesh
        self.mesh = self.create_custom_robot(
            drones_distance, theta, L)

    def update_mesh_stl_mesh(self, drones_distance, theta, L):
        self.mesh = self.create_custom_robot(
            drones_distance, theta, L)  # TODO: should try not to  making a new mesh

    def update_mesh(self, drones_distance, theta, L):
        if self.MESH_TYPE == mesh.Mesh:
            self.update_mesh_stl_mesh(drones_distance, theta, L)
        elif self.MESH_TYPE == Fcl_mesh:
            self.update_mesh_fcl_mesh(drones_distance, theta, L)
        else:
            print("mesh_type is not one of the expected ones...")
            sys.exit()


if __name__ == "__main__":
    pass
