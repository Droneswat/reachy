"""Arm part module.

Implements a Right and a Left Arm.
"""

import numpy as np

from collections import OrderedDict

from .hand import ForceGripper, OrbitaWrist
from .part import ReachyPart
from ..io import SharedLuosIO


hands = {
    'force_gripper': ForceGripper,
    'orbita_wrist': OrbitaWrist,
}


class Arm(ReachyPart):
    """Arm abstraction class.

    Provides high-level access to:
        * ordered list of motors
        * forward and inverse kinematics
    """

    def __init__(self, side, luos_port, dxl_motors, hand):
        """Create a new Arm part.

        Args:
            side (str): 'right' or 'left'
            luos_port (str): serial port where the Luos modules are attached
            dxl_motors (dict): config of the dynamixel motors composing the arm
            hand (str): name of the Hand to attached ('force_gripper', 'orbita_wrist' or it can be None if no hand are attached)
        """
        ReachyPart.__init__(self, name=f'{side}_arm')

        dxl_motors = OrderedDict(dxl_motors)

        # FIXME: forearm_yaw should be removed from the arm part.
        if hand == 'orbita_wrist':
            del dxl_motors['forearm_yaw']

        self.luos_io = SharedLuosIO.with_gate(f'r_{side}_arm', luos_port)
        self.attach_dxl_motors(self.luos_io, dxl_motors)

        if hand is not None and hand not in hands.keys():
            raise ValueError(f'"hand" must be one of {list(hands.keys())} or None!')

        if hand is not None:
            hand_part = hands[hand](luos_port=self.luos_io.port, side=side)
            hand_part.name = f'{self.name}.hand'
            self.motors += hand_part.motors
            self.hand = hand_part

            for m, conf in hands[hand].dxl_motors.items():
                dxl_motors[m] = conf

        else:
            self.hand = None

        self.attach_kinematic_chain(dxl_motors)

    def __repr__(self):
        """Arm representation."""
        return f'<{self.side.capitalize()}Arm "motors": {self.motors} "hand": {self.hand}>'

    def teardown(self):
        """Clean and close the Arm part."""
        self.luos_io.close()

    def forward_kinematics(self, joints_position, use_rad=False):
        """Compute the forward kinematics of the Arm.

        Args:
            joints_position (np.array): angle joints configuration of the arm (in degrees by default)
            use_rad (bool): whether or not to use radians for joints configuration

        .. note:: the end effector will be the end of the Hand if one is attached.

        """
        joints_position = np.array(joints_position)
        if len(joints_position.shape) == 1:
            joints_position = joints_position.reshape(1, -1)

        if not use_rad:
            joints_position = np.deg2rad(joints_position)

        M = self.kin_chain.forward(joints_position)

        if joints_position.shape[0] == 1:
            M = M[0]
        return M

    def inverse_kinematics(self, target_pose, q0=None, use_rad=False):
        """Approximate the inverse kinematics of the Arm.

        Args:
            target_pose (np.array): 4x4 homogeneous pose of the target end effector pose
            q0 (np.array): joint initial angle configurations (used for bootstraping the optimization)
            use_rad (bool): whether or not to use radians for joints configuration

        .. note:: the end effector will be the end of the Hand if one is attached.

        """
        if q0 is None:
            q0 = [m.present_position for m in self.motors]

        q0 = np.array(q0)

        if len(q0.shape) == 1:
            q0 = q0.reshape(1, -1)

        if len(target_pose.shape) == 2:
            target_pose = target_pose.reshape(-1, 4, 4)

        if not use_rad:
            q0 = np.deg2rad(q0)

        J = self.kin_chain.inverse(target_pose, q0)

        if J.shape[0] == 1:
            J = J[0]

        if not use_rad:
            J = np.rad2deg(J)

        return J


class LeftArm(Arm):
    """Left Arm part."""

    dxl_motors = OrderedDict([
        ('shoulder_pitch', {
            'id': 20, 'offset': 90.0, 'orientation': 'direct',
            'link-translation': [0, 0.19, 0], 'link-rotation': [0, 1, 0]
        }),
        ('shoulder_roll', {
            'id': 21, 'offset': -90.0, 'orientation': 'indirect',
            'link-translation': [0, 0, 0], 'link-rotation': [1, 0, 0],
        }),
        ('arm_yaw', {
            'id': 22, 'offset': 0.0, 'orientation': 'indirect',
            'link-translation': [0, 0, 0], 'link-rotation': [0, 0, 1],
        }),
        ('elbow_pitch', {
            'id': 23, 'offset': 0.0, 'orientation': 'direct',
            'link-translation': [0, 0, -0.30745], 'link-rotation': [0, 1, 0],
        }),
        # FIXME: this should be in the hand part.
        ('forearm_yaw', {
            'id': 24, 'offset': 0.0, 'orientation': 'indirect',
            'link-translation': [0, 0, 0], 'link-rotation': [0, 0, 1],
        }),
    ])

    def __init__(self, luos_port, hand=None):
        """Create a new Left Arm part.

        Args:
            luos_port (str): serial port where the Luos modules are attached
            hand (str): name of the Hand to attached ('force_gripper', 'orbita_wrist' or it can be None if no hand are attached)
        """
        Arm.__init__(self, side='left',
                     luos_port=luos_port, dxl_motors=LeftArm.dxl_motors,
                     hand=hand)


class RightArm(Arm):
    """Right Arm part."""

    dxl_motors = OrderedDict([
        ('shoulder_pitch', {
            'id': 10, 'offset': 90.0, 'orientation': 'indirect',
            'link-translation': [0, -0.19, 0], 'link-rotation': [0, 1, 0],
        }),
        ('shoulder_roll', {
            'id': 11, 'offset': 90.0, 'orientation': 'indirect',
            'link-translation': [0, 0, 0], 'link-rotation': [1, 0, 0],
        }),
        ('arm_yaw', {
            'id': 12, 'offset': 0.0, 'orientation': 'indirect',
            'link-translation': [0, 0, 0], 'link-rotation': [0, 0, 1],
        }),
        ('elbow_pitch', {
            'id': 13, 'offset': 0.0, 'orientation': 'indirect',
            'link-translation': [0, 0, -0.30745], 'link-rotation': [0, 1, 0],
        }),
        # FIXME: this should be in the hand part.
        ('forearm_yaw', {
            'id': 14, 'offset': 0.0, 'orientation': 'indirect',
            'link-translation': [0, 0, 0], 'link-rotation': [0, 0, 1],
        }),
    ])

    def __init__(self, luos_port, hand=None):
        """Create a new Right Arm part.

        Args:
            luos_port (str): serial port where the Luos modules are attached
            hand (str): name of the Hand to attached ('force_gripper', 'orbita_wrist' or it can be None if no hand are attached)
        """
        Arm.__init__(self, side='right',
                     luos_port=luos_port, dxl_motors=RightArm.dxl_motors,
                     hand=hand)
