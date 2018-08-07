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

        a = (88.7623, -18.0656, 0.601931)
        b = (87.5712, -18.447, 4.56638)
        c = (91.6581, -15.3077, 1.73722)
        d = (91.4966, -21.1526, 1.12646)

        brl_db.bot(
            "bot.s",
            mode = 3,
            orientation = 1,
            flags = 0,
            vertices = [a, b, c, d],
            faces = [(0, 1, 2), (1, 2, 3), (3, 1, 0)],
            thickness=[2, 3, 1],
            face_mode=[True, True, False]
        )

        brl_db.wedge(
            "wedge1.s",
            vertex=(87, -8.5, 0),
            x_dir=(0, 0, 1),
            z_dir=(0, -1, 0),
            x_len=5, y_len=4, z_len=1,
            x_top_len = 2
            )

        brl_db.arb8(
            'base.s',
            points = [
                      (-90, -150, -2.5), (150, -150, -2.5), (150, 60, -2.5), (-90, 60, -2.5),
                      (-90, -150, -1.2), (150, -150, -1.2), (150, 60, -1.2), (-90, 60, -1.1)]
            )

        brl_db.region(
            "base.r",
            region_id = 123,
            tree = "base.s",
            shader = "mirror {re 0.2}",
            rgb_color = (0, 0, 0)
        )

        
        '''
        brl_db.sketch(
            name = "mysketch",
            base = (0, 0, 0),
            u_vec = (1, 0, 0),
            v_vec = (0, 1, 0),
            vertices = ((0,0), (1, 0), (0, 1), (1,1))
            )
        '''

        brl_db.region(
            'bot.r',
            region_id = 1,
            tree = 'bot.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(240,163,255)
            )

        brl_db.region(
            'arb4.r',
            region_id = 2,
            tree = 'arb4.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(0,117,220)
            )

        brl_db.region(
            'arb5.r',
            region_id = 3,
            tree = 'arb5.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(153,63,0)
            )

        brl_db.region(
            'arb6.r',
            region_id = 4,
            tree = 'arb6.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(76,0,92)
            )

        brl_db.region(
            'arb7.r',
            region_id = 5,
            tree = 'arb7.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(255, 80, 5)
            )

        brl_db.region(
            'arb8.r',
            region_id = 6,
            tree = 'arb8.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(0,92,49)
            )

        brl_db.region(
            'rhc.r',
            region_id = 7,
            tree = 'rhc2.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(43,206,72)
            )

        brl_db.region(
            'rpc.r',
            region_id = 7,
            tree = 'rpc.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(255,204,153)
            )

        brl_db.region(
            'epa.r',
            region_id = 8,
            tree = 'epa.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(128,128,128)
            )

        brl_db.region(
            'ehy.r',
            region_id = 9,
            tree = 'ehy.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(148,255,181)
            )

        brl_db.region(
            'particle.r',
            region_id = 10,
            tree = 'particle.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(143,124,0)
            )

        brl_db.region(
            'rcc.r',
            region_id = 11,
            tree = 'rcc.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(157,204,0)
            )

        brl_db.region(
            'tgc.r',
            region_id = 12,
            tree = 'tgc.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(194,0,136)
            )

        brl_db.region(
            'tec.r',
            region_id = 13,
            tree = 'tec.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(0,51,128)
            )

        brl_db.region(
            'rec.r',
            region_id = 14,
            tree = 'rec.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(255,164,5)
            )

        brl_db.region(
            'trc.r',
            region_id = 15,
            tree = 'trc.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(255,168,187)
            )

        brl_db.region(
            'sph.r',
            region_id = 16,
            tree = 'sph1.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(66,102,0)
            )

        brl_db.region(
            'ellipsoid.r',
            region_id = 17,
            tree = 'ellipsoid.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(255,0,16)
            )

        brl_db.region(
            'ellipsoid2.r',
            region_id = 18,
            tree = 'ellipsoid2.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(94,241,242)
            )


        brl_db.region(
            'torus.r',
            region_id = 19,
            tree = 'torus.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(0,153,143)
            )

        brl_db.region(
            'eto.r',
            region_id = 20,
            tree = 'eto.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(224,255,102)
            )

        brl_db.region(
            'cone.r',
            region_id = 21,
            tree = 'cone.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(116,10,255)
            )

        brl_db.region(
            'cone.r',
            region_id = 22,
            tree = 'cone.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(153, 0, 0)
            )

        brl_db.region(
            'hyperboloid.r',
            region_id = 23,
            tree = 'hyperboloid.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(255, 255, 128)
            )

        brl_db.region(
            'pipe.r',
            region_id = 24,
            tree = 'pipe.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(255, 255, 0)
            )


        brl_db.region(
            'wedge.r',
            region_id = 25,
            tree = 'wedge1.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(255, 0, 96)
            )
        

        brl_db.region(
            name="all.r",
            region_id = 123,
            tree=(
                "bot.s",
                "sph1.s",
                "ellipsoid2.s",
                "wedge1.s",
                "arb4.s",
                "arb5.s",
                "arb6.s",
                "arb7.s",
                "arb8.s",
                "tec.s",
                "rec.s",
                "ellipsoid.s",
                "torus.s",
                "rcc.s",
                "tgc.s",
                "cone.s",
                "trc.s",
                "rpc.s",
                "rhc2.s",
                "epa.s",
                "ehy.s",
                "hyperboloid.s",
                "eto.s",
                "particle.s",
                "pipe.s",
            ),

        )
