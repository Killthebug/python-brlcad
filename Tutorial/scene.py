from brlcad.vmath import Transform
from brlcad.geometry import Database
from brlcad import primitives

if __name__ == "__main__":
    with Database("scene.g", "Test BRLCAD DB file") as brl_db:
        '''
        brl_db.sphere(
            "sph1.s",
            center=(0.5, 5, 8),
            radius=0.75
        )
        brl_db.rpp(
            "box1.s",
            pmin=(0, 0, 0),
            pmax=(2, 4, 2.5)
        )
        brl_db.wedge(
            "wedge1.s",
            vertex=(0, 0, 3.5),
            x_dir=(0, 1, 0),
            z_dir=(0, 0, 1),
            x_len=4, y_len=2, z_len=1,
            x_top_len=3
        )
        '''
        brl_db.arb4(
            "arb4.s",
            points=[(-10, -8.5, 0), (-6, -11, 0), (-6, -6, 0), (-8, -8.5, 6)]
        )
        brl_db.arb5(
            "arb5.s",
            points=[(-10, -20, 0), (-6, -20, 0), (-6, -15, 0), (-10, -15, 0), (-8, -17.5, 6)]
        )
        brl_db.arb6(
            "arb6.s",
            points=[(-10, -30, 0), (-6, -30, 0), (-6, -25, 0), (-10, -25, 0), (-8, -30, 6), (-8, -25, 6)]
        )
        brl_db.arb7(
            "arb7.s",
            points=[(-10, -40, 0), (-6, -40, 0), (-6, -35, 0), (-10, -35, 0), (-9, -37.5, 6), (-7, -40, 6), (-7, -36.5, 6)]
        )
        brl_db.arb8(
            "arb8.s",
            points=[
                (-10, -50, 0), (-6, -50, 0), (-6, -45, 0), (-10, -45, 0),
                (-9, -50, 6), (-7, -50, 6), (-7, -45, 6), (-9, -45, 6)
            ]
        )

        brl_db.arbn(
            "arbn.s",
            planes=[
                [(0, 0, -1), -10],
                [(0, 0, 1), 11],
                [(-1, 0, 0), 0.5],
                [(1, 0, 0), 0.5],
                [(0, -1, 0), 0.5],
                [(0, 1, 0), 0.5],
            ]
        )

        brl_db.rhc("rhc2.s", 
                base = (15, -47.5, 0),
                height = (0, 0, 6),
                breadth =  (2.5, 0, 0),
                half_width = 2.5,
                asymptote = 0.1
        )

        brl_db.rpc("rpc.s",
            base=(15, -37.5, 0),
            height=(0, 0, 6),
            breadth=(2.5, 0, 0),
            half_width= 2.5
        )

        brl_db.epa(
            "epa.s",
            base=(15, -27.5, 0),
            height=(0, 0, 6),
            n_major=(1, 0, 0),
            r_major=3,
            r_minor=2
        )
        brl_db.ehy(
            "ehy.s",
            base=(15, -17.5, 0),
            height=(0, 0, 6),
            n_major=(1, 0, 0),
            r_major=3, r_minor=2,
            asymptote=0.1
        )

        brl_db.particle(
            "particle.s",
            base=(15, -8.5, 1.25),
            height=(0, 0, 2.5),
            r_base=2.5,
            r_end=1.5
        )

        brl_db.rcc(
            "rcc.s",
            base= (40, -47.5, 0),
            height= (0, 0, 6),
            radius= 2.5
        )

        brl_db.tgc(
            "tgc.s",
            base=(40, -37.5, 0),
            height=(0, 0, 6),
            a=(1, 0, 0),
            b=(0, 2, 0),
            c=(2, 0, 0),
            d=(0, 1, 0)
        )
        '''
        TEC is a special case of TGC
        '''
        brl_db.tgc(
            "tec.s",
            base=(40, -27.5, 0),
            height=(0, 0, 6),
            a=(1, 0, 0),
            b=(0, 3, 0),
            c=(1, 0, 0),
            d=(0, 1.5, 0)
        )

        '''
        REC is a special case of TGC
        '''
        brl_db.tgc(
            'rec.s',
            base=(40, -17.5, 0),
            height=(0, 0, 6),
            a=(1, 0, 0),
            b=(0, 2, 0),
            c=(1, 0, 0),
            d=(0, 2, 0)
            )

        brl_db.trc(
            "trc.s",
            base=(40, -8.5, 0),
            height=(0, 0, 6),
            r_base=1.25,
            r_top=2.5
        )

        brl_db.sphere(
            "sph1.s",
            center = (65, -47.5, 2.5),
            radius = 3
        )

        brl_db.ellipsoid(
            "ellipsoid.s",
            center=(65, -37.5, 2.5),
            a=(3, 0, 0),
            b=(0, 3, 0),
            c=(0, 0, 2)
        )

        brl_db.ellipsoid(
            "ellipsoid2.s",
            center=(65, -27.5, 2.5),
            a=(2, 0, 0),
            b=(0, 2, 0),
            c=(0, 0, 3)
        )

        brl_db.torus(
            "torus.s",
            center=(65, -17.5, 2.5),
            n=(0, 0, 1),
            r_revolution=2.25,
            r_cross=1
        )

        brl_db.eto(
            "eto.s",
            center=(65, -8.5, 2.5),
            n=(0, 0, 1),
            s_major=(1, 0, 1),
            r_revolution=2.25,
            r_minor=0.50
        )

        brl_db.cone(
            "cone.s",
            base=(90, -47.5, 0),
            n=(0, 0, 1),
            h=6,
            r_base=2.5,
            r_top=0
        )

        brl_db.hyperboloid(
            "hyperboloid.s",
            base=(90, -37.5, 0),
            height=(0, 0, 6),
            a_vec=(1.5, 1, 0),
            b_mag=1,
            base_neck_ratio=0.3
        )

        brl_db.pipe(
            "pipe.s",
            points=[
                [(87.4337, -28.1268, 1.01347), 0.604139, 0, 2.71863],
                [(87.4547, -30.8446, 1.24826), 0.604139, 0, 2.71863],
                [(92.8908, -30.8003, 1.71279), 0.604139, 0, 2.71863],
                [(92.8468, -25.3618, 2.14942), 0.604139, 0, 2.71863],
                [(87.4088, -25.4035, 2.59109), 0.604139, 0, 2.71863],
                [(87.4508, -30.8392, 3.06066), 0.604139, 0, 2.71863],
                [(92.8869, -30.7948, 3.5252), 0.604139, 0, 2.71863],
                [(92.843, -25.3564, 3.96183), 0.604139, 0, 2.71863],
                [(87.4049, -25.398, 4.4035), 0.604139, 0, 2.71863],
                [(87.4259, -28.1159, 4.63828), 0.604139, 0, 2.71863],
            ]
        )

        brl_db.bot(
            "bot.s",
            mode = 3,
            orientation = 1,
            flags = 0,
            vertices = [(0, 5, 5), (0, 5, 6), (0, 6, 5), (1, 5, 5)],
            faces = [(0, 1, 2), (1, 2, 3), (3, 1, 0)],
            thickness=[2, 3, 1],
            face_mode=[True, True, False]
        )
        
        '''

        brl_db.ebm(
            "text1.s",
            file_name = "ychar.bw",
            x_dim = 10,
            y_dim = 10,
            tallness = 0.3)

        brl_db.submodel(
            "submodel.s",
            file_name = "db.g",
            treetop = "arb4.s",
            )

        brl_db.sketch(
            name = "mysketch",
            base = (0, 0, 0),
            u_vec = (1, 0, 0),
            v_vec = (0, 1, 0),
            vertices = ((0,0), (1, 0), (0, 1), (1,1))
            )

        '''

        '''
        Error : ctypes.ArgumentError: argument 6: <type 'exceptions.TypeError'>: expected LP_c_double_Array_5 instance instead of LP_c_double_Array_5

        brl_db.metaball(
            "metaball.s",      
            points=[[(1, 1, 1), 1, 0], [(0, 0, 1), 2, 0]],
            threshold=1, 
            method=2, 
        )
        '''

        '''
        brl_db.half(
            "half.s",
            norm = (0, 0, 1), 
            d = -1
        )
        '''
