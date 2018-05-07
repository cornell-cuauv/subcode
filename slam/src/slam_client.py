import zmq
import proto.slam_msg_pb2 as slam_msg

class SlamClient:

    def __init__(self):
        self.ctx = zmq.Context()
        self.socket = self.ctx.socket(zmq.REQ)
        self.socket.connect("tcp://127.0.0.1:57411")

    def observe(self, obj_id, m_x, m_y, m_z, u_x, u_y, u_z):

        msg = slam_msg.SlamMsg()
        msg.id = obj_id
        msg.m_x = m_x
        msg.m_y = m_y
        msg.m_z = m_z
        msg.u_x = u_x
        msg.u_y = u_y
        msg.u_z = u_z

        self.socket.send(msg.SerializeToString())
        msg = self.socket.recv()
        print(msg)

    def test(self):
        self.observe("Object", 10, 20, 30, 40, 50, 60)
