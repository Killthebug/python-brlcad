from brlcad.vmath import Transform
from brlcad.geometry import Database
from brlcad import primitives
from brlcad.primitives.sketch import *

if __name__ == "__main__":
    with Database("test_wdb.g", "Test BRLCAD DB file") as brl_db:
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
        brl_db.arb4(
            "arb4.s",
            points=[(-1, -5, 3), (1, -5, 3), (1, -3, 4), (0, -4, 5)]
        )
        brl_db.arb5(
            "arb5.s",
            points=[(-1, -5, 0), (1, -5, 0), (1, -3, 0), (-1, -3, 0), (0, -4, 3)]
        )
        brl_db.arb6(
            "arb6.s",
            points=[(-1, -2.5, 0), (1, -2.5, 0), (1, -0.5, 0), (-1, -0.5, 0), (0, -2.5, 2.5), (0, -0.5, 2.5)]
        )
        brl_db.arb7(
            "arb7.s",
            points=[(-1, -2.5, 3), (1, -2.5, 3), (1, -0.5, 3), (-1, -1.5, 3), (-1, -2.5, 5), (1, -2.5, 5), (1, -1.5, 5)]
        )
        brl_db.arb8(
            "arb8.s",
            points=[
                (-1, -1, 5), (1, -1, 5), (1, 1, 5), (-1, 1, 5),
                (-0.5, -0.5, 6.5), (0.5, -0.5, 6.5), (0.5, 0.5, 6.5), (-0.5, 0.5, 6.5)
            ]
        )
        brl_db.ellipsoid(
            "ellipsoid.s",
            center=(0, -4, 6),
            a=(0.75, 0, 0),
            b=(0, 1, 0),
            c=(0, 0, 0.5)
        )
        brl_db.torus(
            "torus.s",
            center=(0, -2, 6),
            n=(0, 0, 1),
            r_revolution=1,
            r_cross=0.25
        )
        brl_db.rcc(
            "rcc.s",
            base=(1, 2, 5),
            height=(0, 0, 1),
            radius=1
        )
        brl_db.tgc(
            "tgc.s",
            base=(0, -5, 7),
            height=(0, 0, 1),
            a=(0.5, 0, 0),
            b=(0, 1, 0),
            c=(1, 0, 0),
            d=(0, 0.5, 0)
        )
        brl_db.cone(
            "cone.s",
            base=(0, -2, 7),
            n=(0, 0, 2),
            h=0.5,
            r_base=1.25,
            r_top=0.75
        )
        brl_db.trc(
            "trc.s",
            base=(0, -2, 7.5),
            height=(0, 0, 0.5),
            r_base=0.75,
            r_top=1.25
        )
        brl_db.rpc(
            "rpc.s",
            base=(0, -2, 8.5),
            height=(0, 0, 0.5),
            breadth=(0.25, 0.25, 0),
            half_width=0.75
        )
        brl_db.rhc(
            "rhc.s",
            base=(0, -2, 9),
            height=(0, 0, 0.5),
            breadth=(0.25, 0.25, 0),
            half_width=0.75,
            asymptote=0.1
        )
        brl_db.epa(
            "epa.s",
            base=(1, 2, 7),
            height=(0, 0, -1),
            n_major=(1, 0, 0),
            r_major=1,
            r_minor=0.5
        )
        brl_db.ehy(
            "ehy.s",
            base=(1, 2, 7),
            height=(0, 0, 1),
            n_major=(1, 0, 0),
            r_major=1, r_minor=0.5,
            asymptote=0.1
        )
        brl_db.hyperboloid(
            "hyperboloid.s",
            base=(0, 0, 6.75),
            height=(0, 0, 0.75),
            a_vec=(1, 0, 0),
            b_mag=0.5,
            base_neck_ratio=0.3
        )
        brl_db.eto(
            "eto.s",
            center=(1, 2, 8.5),
            n=(0, 0, 1),
            s_major=(0.5, 0, 0.5),
            r_revolution=1,
            r_minor=0.25
        )
        brl_db.arbn(
            "arbn.s",
            planes=[
                [(0, 0, -1), -8],
                [(0, 0, 1), 9],
                [(-1, 0, 0), 0.5],
                [(1, 0, 0), 0.5],
                [(0, -1, 0), 0.5],
                [(0, 1, 0), 0.5],
            ]
        )
        brl_db.particle(
            "particle.s",
            base=(0, -5, 8.5),
            height=(0, 0, 0.75),
            r_base=0.25,
            r_end=0.5
        )
        brl_db.pipe(
            "pipe.s",
            points=[
                [(0.55, 4, 5.45), 0.1, 0, 0.45],
                [(0.55, 3.55, 5.4875), 0.1, 0, 0.45],
                [(1.45, 3.55, 5.5625), 0.1, 0, 0.45],
                [(1.45, 4.45, 5.6375), 0.1, 0, 0.45],
                [(0.55, 4.45, 5.7125), 0.1, 0, 0.45],
                [(0.55, 3.55, 5.7875), 0.1, 0, 0.45],
                [(1.45, 3.55, 5.8625), 0.1, 0, 0.45],
                [(1.45, 4.45, 5.9375), 0.1, 0, 0.45],
                [(0.55, 4.45, 6.0125), 0.1, 0, 0.45],
                [(0.55, 4, 6.05), 0.1, 0, 0.45],
            ]
        )
        
        '''
        To Complete : 
        brl_db.ars(
            "ars.s", 
            curves=[]
        )
        '''

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

        brl_db.grip(
            "grip.s",
            center = (0, 5, 1),
            normal = (1, 0, 0),
            magnitude = 3,
        )

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

        mysketch = primitives.Sketch("gg.s",
            base = (0, 0, -4.99),
            u_vec = (1, 0, 0),
            v_vec = (0, 1, 0),
            vertices = [
            (0.59800664451827234557868 ,-4.674418604651163100527356),
            (2.501661129568105934595224, -1.833887043189368792894811),
            (6.259136212624585304808988, -3.109634551495016552280504),
            (2.581395348837209002823556, -3.209302325581395720632827),
            (5.830564784053156479615154,-5.571428571428572062984586),
            (5.521594684385382478808424, -1.764119601328903774728474),
            (2.531561461794019862736604, -0.9966777408637871316088308),
            (0.1594684385382059976787872, 0.2691029900332225777148665),
            (-2.720930232558139483245441, -1.495016611295681085991305),
            (1.764119601328903774728474, -1.016611295681063120710519),
            (0.239202657807309121418271, -2.730897009966777755352041),
            (1.9634551495016612232547, -2.501661129568106378684433),
            (-1.265780730897009931368302, -2.611295681063122930964937)],
            )

        c1 = Curve(mysketch, [0,1])
        l1 = Line(mysketch, c1)

        newsketch = primitives.Sketch("gg.s",
            base = (0, 0, -4.99),
            u_vec = (1, 0, 0),
            v_vec = (0, 1, 0),
            vertices = [
            (0.59800664451827234557868 ,-4.674418604651163100527356),
            (2.501661129568105934595224, -1.833887043189368792894811),
            (6.259136212624585304808988, -3.109634551495016552280504),
            (2.581395348837209002823556, -3.209302325581395720632827),
            (5.830564784053156479615154,-5.571428571428572062984586),
            (5.521594684385382478808424, -1.764119601328903774728474),
            (2.531561461794019862736604, -0.9966777408637871316088308),
            (0.1594684385382059976787872, 0.2691029900332225777148665),
            (-2.720930232558139483245441, -1.495016611295681085991305),
            (1.764119601328903774728474, -1.016611295681063120710519),
            (0.239202657807309121418271, -2.730897009966777755352041),
            (1.9634551495016612232547, -2.501661129568106378684433),
            (-1.265780730897009931368302, -2.611295681063122930964937)],
            curves = [["line", [0,1]]]
            )


        brl_db.sketch(
            name = "newsketch",
            sketch = newsketch
            )

        brl_db.superell(
            "superell.s",
            center = (0, 5.5, 3),
            a = (1, 0, 0),
            b = (0, 1, 0),
            c = (0, 0, 1),
            n = 0,
            e = 0
        )

        '''
        Error : ctypes.ArgumentError: argument 6: <type 'exceptions.TypeError'>: expected LP_c_double_Array_5 instance instead of LP_c_double_Array_5

        brl_db.metaball(
            "metaball.s",      
            points=[[(1, 1, 1), 1, 0], [(0, 0, 1), 2, 0]],
            threshold=1, 
            method=2, 
        )
        '''

        brl_db.half(
            "half.s",
            norm = (0, 0, 1), 
            d = -1
        )

        brl_db.region(
            name="all.r",
            tree=(
                "bot.s",
                "sph1.s",
                "box1.s",
                "wedge1.s",
                "arb4.s",
                "arb5.s",
                "arb6.s",
                "arb7.s",
                "arb8.s",
                "ellipsoid.s",
                "torus.s",
                "rcc.s",
                "tgc.s",
                "cone.s",
                "trc.s",
                "rpc.s",
                "rhc.s",
                "epa.s",
                "ehy.s",
                "hyperboloid.s",
                "eto.s",
                primitives.leaf("arbn.s", Transform.translation(1, 0, 0)),
                "particle.s",
                "pipe.s",
            ),
            shader="plastic {di .8 sp .2}",
            rgb_color=(64, 180, 96)
        )
