# IGRF-13 synthesis - file format, recurrences, transforms, check values

Companion to `SKILL.md`. Everything here is class-level: it applies to any
geodetic point and any epoch in 1900.0-2025.0 covered by IGRF-13 (Alken et al.
2021, doi:10.1186/s40623-020-01288-x). No value here is the answer to any
particular task.

## Coefficient file (`igrf13coeffs.txt`)

Two header lines, then one line per coefficient:

```
g/h   n   m   v(1900.0) v(1905.0) ... v(2015.0) v(2020.0)   SV(2020-2025)
```

- `g` lines are cosine coefficients, `h` lines sine coefficients.
- `n` = 1..13 (degree), `m` = 0..n (order). For `m = 0` there is no `h` term.
- 25 value columns at the 5-year epochs 1900.0, 1905.0, ..., 2020.0, in nT.
- 1 secular-variation column, nT/yr, valid 2020.0-2025.0.

The coefficient set is IGRF-13 (IAGA Working Group V-MOD; Alken et al. 2021,
*Earth, Planets and Space* 73:49, doi:10.1186/s40623-020-01288-x).

## Coefficients at an arbitrary epoch t

The epoch nodes and the secular-variation column are part of IGRF-13 (Alken et
al. 2021):

```
t on a node (e.g. 2010.0)            -> take that column
t between nodes t0 < t < t1          -> g = g0 + (t-t0)/(t1-t0) * (g1 - g0)
t > 2020.0 (up to 2025.0)            -> g = g(2020.0) + (t - 2020.0) * SV
```

## Geodetic -> geocentric (WGS84)

WGS84 defining parameters (NGA TR8350.2, 2014): `a = 6378.137` km,
`e^2 = 0.00669437999014`, `b = a*sqrt(1-e^2)`.

```
s2 = sin(lat_gd)^2 ; c2 = cos(lat_gd)^2
tmp   = h * sqrt(a^2*c2 + b^2*s2)
beta  = atan( (tmp + b^2)/(tmp + a^2) * tan(lat_gd) )
theta = pi/2 - beta                       # geocentric colatitude (rad)
r     = sqrt( h^2 + 2*tmp + a^2*(1 - (1-(b/a)^4)*s2) / (1 - (1-(b/a)^2)*s2) )   # km
```

## Schmidt semi-normalised Legendre functions

Gauss-normalised recurrence (in `ct = cos(theta)`, `st = sin(theta)`):

```
P[0,0]=1, dP[0,0]=0
diagonal (n=m):  P[n,n]  = st*P[n-1,n-1]
                 dP[n,n] = st*dP[n-1,n-1] + ct*P[n-1,n-1]
off-diagonal (m<n):
   K = 0                                   if n==1
   K = ((n-1)^2 - m^2)/((2n-1)(2n-3))      if n>1
   P[n,m]  = ct*P[n-1,m]  - K*P[n-2,m]
   dP[n,m] = ct*dP[n-1,m] - st*P[n-1,m] - K*dP[n-2,m]
```

Schmidt factor (apply after the recurrence):

```
S[0,0]=1
S[n,0] = S[n-1,0]*(2n-1)/n
S[n,m] = S[n,m-1]*sqrt((n-m+1)*(1+[m==1])/(n+m))      # m>=1, [m==1] is 1 when m==1 else 0
P[n,m]  *= S[n,m] ;  dP[n,m] *= S[n,m]
```

## Field synthesis (geocentric components, nT)

`RE = 6371.2` km (the IGRF geomagnetic reference radius; Alken et al. 2021);
`ratio = RE/r`:

```
Br     =  sum_{n=1..13} sum_{m=0..n}  ratio^(n+2) * (n+1) * (g[n,m]*cos(m*lon) + h[n,m]*sin(m*lon)) * P[n,m]
Btheta = -sum ratio^(n+2) * (g[n,m]*cos(m*lon) + h[n,m]*sin(m*lon)) * dP[n,m]
Bphi   = -sum ratio^(n+2) * m * (-g[n,m]*sin(m*lon) + h[n,m]*cos(m*lon)) * P[n,m] / sin(theta)
```

## Rotate the field to the geodetic frame

`Bphi` is already geographic east. Rotate `(Btheta, Br)` into geodetic
north/up. With the same WGS84 `a`, `E2 = 1-(b/a)^2`, `GCLAT = 90 - theta_deg`,
`RI = a/r`:

```
A21=(512E2+128E4+60E6+35E8)/1024   A22=(E6+E8)/32          A23=-3(4E6+3E8)/256
A41=-(64E4+48E6+35E8)/1024         A42=(4E4+2E6+E8)/16     A43=15E8/256   A44=-E8/16
A61=3(4E6+5E8)/1024                A62=-3(E6+E8)/32        A63=35(4E6+3E8)/768
A81=-5E8/2048  A82=64E8/2048  A83=-252E8/2048  A84=320E8/2048
A2=RI(A21+RI(A22+RI*A23)) ; A4=RI(A41+RI(A42+RI(A43+RI*A44)))
A6=RI(A61+RI(A62+RI*A63)) ; A8=RI(A81+RI(A82+RI(A83+RI*A84)))
SCL=sin(GCLAT); CCL=cos(GCLAT)
S2CL=2 SCL CCL; C2CL=2CCL^2-1; S4CL=2 S2CL C2CL; C4CL=2 C2CL^2-1
S8CL=2 S4CL C4CL; S6CL=S2CL C4CL + C2CL S4CL
DLTCL = S2CL*A2 + S4CL*A4 + S6CL*A6 + S8CL*A8
gdlat = DLTCL + radians(GCLAT)
psi   = sin(gdlat)*sin(theta) - cos(gdlat)*cos(theta)
Bnorth = -cos(psi)*Btheta - sin(psi)*Br
Bup    = -sin(psi)*Btheta + cos(psi)*Br
```

Then `X = Bnorth`, `Y = Bphi`, `Z = -Bup`, and

```
D = atan2(Y, X)            # declination (east +)
I = atan2(Z, hypot(X,Y))   # inclination (down +)
H = hypot(X, Y)            # horizontal intensity
F = sqrt(X^2 + Y^2 + Z^2)  # total intensity
```

## Check values (independent points, not any task's stations)

Sea-level unless noted; verify your implementation reproduces these before
trusting it on the task coordinates.

| epoch  | lat    | lon   | h(km) | D (deg)  | I (deg)  | H (nT)  | F (nT)  |
|--------|--------|-------|-------|----------|----------|---------|---------|
| 2020.0 |  45.0  |   0.0 | 0.0   |  +0.533  | +60.491  | 23065.8 | 46828.6 |
| 2020.0 |   0.0  |   0.0 | 0.0   |  -4.654  | -30.093  | 27631.1 | 31935.5 |
| 2015.0 | -33.0  |  18.0 | 0.0   | -23.898  | -66.159  | 10390.0 | 25705.2 |
| 2022.5 |  52.0  |  13.0 | 1.0   |  +4.532  | +67.576  | 18976.6 | 49748.3 |

If your `D` at the (45N, 0E) sea-level check point is off by a couple tenths of a
degree, you skipped the geodetic conversion; if it is off by several degrees, your
Schmidt normalisation is wrong.
