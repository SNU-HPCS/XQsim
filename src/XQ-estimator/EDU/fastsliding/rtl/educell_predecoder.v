`include "define.v"


module educell_predecoder (
    location,
    pchinfo,
    role,
    possible_dir, 
    syn_to_west, 
    syn_to_east, 
    first_aqmeas_flag
);

localparam EDUPI_BW = `PCHTYPE_BW + (4*`FACEBD_BW);

/*** INPUT/OUTPUT DECLARATION***/
input [6:0] location;
input [EDUPI_BW-1:0] pchinfo;
output reg [1:0] role;
output reg [5:0] possible_dir; // (nw, ne, sw, se, n, s) 
output reg [1:0] syn_to_west;
output reg [1:0] syn_to_east;
output reg first_aqmeas_flag;


/*** WIRE DECLARATION & ASSIGN***/
wire even, west, north, east, south; // For Distillation block
assign {even, west, north, east, south} = location[6 -: 5];

wire [`PCHTYPE_BW-1:0] pchtype;
wire [`FACEBD_BW-1:0] facebd_w, facebd_n, facebd_e, facebd_s;
assign {pchtype, facebd_w, facebd_n, facebd_e, facebd_s} = pchinfo;

wire is_pchtype_a;
assign is_pchtype_a = (pchtype == `PCHTYPE_AW | pchtype == `PCHTYPE_AC | pchtype == `PCHTYPE_AE | pchtype == `PCHTYPE_AWE);

/*** WIRE TRANSFER (COMBINATIONAL LOGIC) ***/
always @(*)
begin
    // role, possible_dir
    //// ZT
    if (pchtype == `PCHTYPE_ZT)
    begin
        if (north & west) // NW 
		begin
            role = `ROLE_INACTIVE;
            possible_dir = {1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0};
        end
        else if (north & ~east) // N
        begin
            if (even)
                role = `ROLE_ACTIVE;
            else
                role = `ROLE_BOUNDARY;
            possible_dir = {1'b0, 1'b0, 1'b1, 1'b1, 1'b0, 1'b0};
        end
        else if (north & east) // NE 
        begin
            role = `ROLE_BOUNDARY;
            if (facebd_e == `FACEBD_MP)
                possible_dir = {1'b0, 1'b0, 1'b1, 1'b1, 1'b0, 1'b0};
            else
                possible_dir = {1'b0, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0};
        end
        else if (west & ~south) // W
        begin
            if (even)
                role = `ROLE_ACTIVE;
            else
                role = `ROLE_BOUNDARY;
            possible_dir = {1'b0, 1'b1, 1'b0, 1'b1, 1'b0, 1'b0};
        end
        else if (east & ~south) // E
        begin
            if (facebd_e == `FACEBD_MP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
            end
            else
            begin
                if (even)
                    role = `ROLE_BOUNDARY;
                else
                    role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0};
            end
        end
        else if (west & south) // SW
        begin
            role = `ROLE_BOUNDARY;
            possible_dir = {1'b0, 1'b1, 1'b0, 1'b1, 1'b0, 1'b0};
        end
        else if (south & ~east) // S
        begin
            role = `ROLE_ACTIVE;
            possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
        end
        else if (south & east) // SE
        begin
            if (facebd_e == `FACEBD_MP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b1, 1'b1, 1'b0, 1'b0, 1'b1};
            end
            else
            begin
                role = `ROLE_BOUNDARY;
                possible_dir = {1'b1, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0};
            end
        end
        else // C
        begin
            role = `ROLE_ACTIVE;
            possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
        end
    end
    //// ZB
    else if (pchtype == `PCHTYPE_ZB)
    begin
        if (north & west) // NW
        begin
            role = `ROLE_BOUNDARY;
            possible_dir = {1'b0, 1'b1, 1'b0, 1'b1, 1'b0, 1'b0};
        end
        else if (north & ~east) // N
        begin
            role = `ROLE_ACTIVE;
            possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
        end
        else if (north & east) // NE
        begin
            if (facebd_e == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b0, 1'b1, 1'b1, 1'b1, 1'b0};
            end
            else
            begin
                role = `ROLE_BOUNDARY;
                possible_dir = {1'b1, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0};
            end
        end
        else if (west & ~south) // W
        begin
            if (even)
                role = `ROLE_BOUNDARY;
            else
                role = `ROLE_ACTIVE;
            possible_dir = {1'b0, 1'b1, 1'b0, 1'b1, 1'b0, 1'b0};
        end
        else if (east & ~south) // E
        begin
            if (facebd_e == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
            end
            else
            begin
                if (even)
                    role = `ROLE_ACTIVE;
                else
                    role = `ROLE_BOUNDARY;
                possible_dir = {1'b1, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0};
            end
        end
        else if (west & south) // SW
        begin
            role = `ROLE_INACTIVE;
            possible_dir = {1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0};
        end
        else if (south & ~east) // S
        begin
            if (even)
                role = `ROLE_BOUNDARY;
            else
                role = `ROLE_ACTIVE;
            possible_dir = {1'b1, 1'b1, 1'b0, 1'b0, 1'b0, 1'b0};
        end
        else if (south & east) // SE
        begin
            role = `ROLE_BOUNDARY;
            if (facebd_e == `FACEBD_PP)
                possible_dir = {1'b1, 1'b1, 1'b0, 1'b0, 1'b0, 1'b0};
            else
                possible_dir = {1'b1, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0};
        end
        else // C
        begin
            role = `ROLE_ACTIVE;
            possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
        end
    end
    //// MT
    else if (pchtype == `PCHTYPE_MT)
    begin
        if (north & west) // NW
        begin
            if (facebd_w == `FACEBD_MP)
                role = `ROLE_ACTIVE;
            else
                role = `ROLE_BOUNDARY;
            possible_dir = {1'b0, 1'b0, 1'b1, 1'b1, 1'b0, 1'b0};
        end
        else if (north & ~east) // N
        begin
            if (even)
                role = `ROLE_ACTIVE;
            else
                role = `ROLE_BOUNDARY;
            possible_dir = {1'b0, 1'b0, 1'b1, 1'b1, 1'b0, 1'b0};
        end
        else if (north & east) // NE
        begin
            role = `ROLE_BOUNDARY;
            possible_dir = {1'b0, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0};
        end
        else if (west & ~south) // W
        begin
            if (facebd_w == `FACEBD_MP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
            end
            else
            begin
                if (even)
                    role = `ROLE_BOUNDARY;
                else
                    role = `ROLE_ACTIVE;
                possible_dir = {1'b0, 1'b1, 1'b0, 1'b1, 1'b0, 1'b0};
            end
        end
        else if (east & ~south) // E
        begin
            if (even)
                role = `ROLE_ACTIVE;
            else
                role = `ROLE_BOUNDARY;
            possible_dir = {1'b1, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0};
        end
        else if (west & south) // SW
        begin
            role = `ROLE_ACTIVE;
            if (facebd_w == `FACEBD_MP)
                possible_dir = {1'b1, 1'b1, 1'b0, 1'b0, 1'b0, 1'b1};
            else
                possible_dir = {1'b0, 1'b1, 1'b0, 1'b0, 1'b0, 1'b1};
        end
        else if (south & ~east) // S
        begin
            role = `ROLE_ACTIVE;
            possible_dir = {1'b1, 1'b1, 1'b0, 1'b0, 1'b0, 1'b1};
        end
        else if (south & east) // SE
        begin
            if (facebd_w == `FACEBD_MP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b0, 1'b0, 1'b0, 1'b0, 1'b1};
            end
            else
            begin
                role = `ROLE_BOUNDARY;
                possible_dir = {1'b1, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0};
            end
        end
        else // C
        begin
            role = `ROLE_ACTIVE;
            possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
        end
    end
    //// MB
    else if (pchtype == `PCHTYPE_MB)
    begin
        if (north & west) // NW
        begin
            if (facebd_n == `FACEBD_LP & facebd_w == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b0, 1'b0, 1'b1, 1'b1, 1'b1, 1'b0};
            end
            else if (facebd_n == `FACEBD_LP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b0, 1'b0, 1'b0, 1'b1, 1'b1, 1'b0};
            end
            else
            begin
                role = `ROLE_BOUNDARY;
                possible_dir = {1'b0, 1'b0, 1'b0, 1'b1, 1'b0, 1'b0};
            end
        end
        else if (north & ~east) // N
        begin
            if (facebd_n == `FACEBD_LP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b0, 1'b0, 1'b1, 1'b1, 1'b1, 1'b0};
            end
            else
            begin
                if (even)
                    role = `ROLE_BOUNDARY;
                else
                    role = `ROLE_ACTIVE;
                possible_dir = {1'b0, 1'b0, 1'b1, 1'b1, 1'b0, 1'b0};
            end
        end
        else if (north & east) // NE
        begin
            if (facebd_e == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b0, 1'b0, 1'b1, 1'b1, 1'b1, 1'b0};
            end
            else
            begin
                role = `ROLE_BOUNDARY;
                possible_dir = {1'b0, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0};
            end
        end
        else if (west & ~south) // W
        begin
            if (facebd_w == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
            end
            else
            begin
                if (even)
                    role = `ROLE_ACTIVE;
                else
                    role = `ROLE_BOUNDARY;
                possible_dir = {1'b0, 1'b1, 1'b0, 1'b1, 1'b0, 1'b0};
            end
        end
        else if (east & ~south) // E
        begin
            if (facebd_e == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
            end
            else
            begin
                if (even)
                    role = `ROLE_ACTIVE;
                else
                    role = `ROLE_BOUNDARY;
                possible_dir = {1'b1, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0};
            end
        end
        else if (west & south) // SW
        begin
            if (facebd_w == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b1, 1'b0, 1'b0, 1'b0, 1'b0};
            end
            else
            begin
                role = `ROLE_BOUNDARY;
                possible_dir = {1'b0, 1'b1, 1'b0, 1'b0, 1'b0, 1'b0};
            end
        end
        else if (south & ~east) // S
        begin
            if (even)
                role = `ROLE_BOUNDARY;
            else
                role = `ROLE_ACTIVE;
            possible_dir = {1'b1, 1'b1, 1'b0, 1'b0, 1'b0, 1'b0};
        end
        else if (south & east) // SE
        begin
            role = `ROLE_BOUNDARY;
            if (facebd_w == `FACEBD_PP)
                possible_dir = {1'b1, 1'b1, 1'b0, 1'b0, 1'b0, 1'b0};
            else
                possible_dir = {1'b1, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0};
        end
        else // C
        begin
            role = `ROLE_ACTIVE;
            possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
        end

    end
    //// M
    else if (pchtype == `PCHTYPE_M)
    begin
        if (north & west) // NW
        begin
            role = `ROLE_BOUNDARY;
            if (facebd_n == `FACEBD_PP)
                possible_dir = {1'b0, 1'b1, 1'b0, 1'b1, 1'b0, 1'b0};
            else
                possible_dir = {1'b0, 1'b0, 1'b0, 1'b1, 1'b0, 1'b0};
        end
        else if (north & ~east) // N
        begin
            if (facebd_n == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
            end
            else
            begin
                if (even)
                    role = `ROLE_ACTIVE;
                else
                    role = `ROLE_BOUNDARY;
                possible_dir = {1'b0, 1'b0, 1'b1, 1'b1, 1'b0, 1'b0};
            end
        end
        else if (north & east) // NE
        begin
            if (facebd_n == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0};
            end
            else
            begin
                role = `ROLE_BOUNDARY;
                possible_dir = {1'b0, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0};
            end
        end
        else if (west & ~south) // W
        begin
            if (even)
                role = `ROLE_BOUNDARY;
            else
                role = `ROLE_ACTIVE;
            possible_dir = {1'b0, 1'b1, 1'b0, 1'b1, 1'b0, 1'b0};
        end
        else if (east & ~south) // E
        begin
            if (even)
                role = `ROLE_BOUNDARY;
            else
                role = `ROLE_ACTIVE;
            possible_dir = {1'b1, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0};
        end
        else if (west & south) // SW
        begin
            if (facebd_s == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b0, 1'b1, 1'b0, 1'b1, 1'b0, 1'b0};
            end
            else
            begin
                role = `ROLE_BOUNDARY;
                possible_dir = {1'b0, 1'b1, 1'b0, 1'b0, 1'b0, 1'b0};
            end
        end
        else if (south & ~east) // S
        begin
            if (facebd_s == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
            end
            else
            begin
                if (even)
                    role = `ROLE_ACTIVE;
                else
                    role = `ROLE_BOUNDARY;
                possible_dir = {1'b1, 1'b1, 1'b0, 1'b0, 1'b0, 1'b0};
            end
        end
        else if (south & east) // SE
        begin
            role = `ROLE_BOUNDARY;
            if (facebd_s == `FACEBD_PP)
                possible_dir = {1'b1, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0};
            else
                possible_dir = {1'b1, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0};
        end
        else // C
        begin
            role = `ROLE_ACTIVE;
            possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
        end
    end
    //// X
    else if (pchtype == `PCHTYPE_X)
    begin
        if (north & west) // NW
        begin
            role = `ROLE_BOUNDARY;
            possible_dir = {1'b0, 1'b0, 1'b1, 1'b1, 1'b0, 1'b0};
        end
        else if (north & ~east) // N
        begin
            if (even)
                role = `ROLE_BOUNDARY;
            else
                role = `ROLE_ACTIVE;
            possible_dir = {1'b0, 1'b0, 1'b1, 1'b1, 1'b0, 1'b0};
        end
        else if (north & east) // NE
        begin
            role = `ROLE_BOUNDARY;
            possible_dir = {1'b0, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0};
        end
        else if (west & ~south) // W
        begin
            if (facebd_w == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
            end
            else
            begin
                if (even)
                    role = `ROLE_ACTIVE;
                else
                    role = `ROLE_BOUNDARY;
                possible_dir = {1'b0, 1'b1, 1'b0, 1'b1, 1'b0, 1'b0};
            end
        end
        else if (east & ~south) // E
        begin
            if (even)
                role = `ROLE_ACTIVE;
            else
                role = `ROLE_BOUNDARY;
            possible_dir = {1'b1, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0};
        end
        else if (west & south) // SW
        begin
            if (facebd_w == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b1, 1'b0, 1'b0, 1'b0, 1'b0};
            end
            else
            begin
                role = `ROLE_BOUNDARY;
                possible_dir = {1'b0, 1'b1, 1'b0, 1'b0, 1'b0, 1'b0};
            end
        end
        else if (south & ~east) // S
        begin
            if (even)
                role = `ROLE_BOUNDARY;
            else
                role = `ROLE_ACTIVE;
            possible_dir = {1'b1, 1'b1, 1'b0, 1'b0, 1'b0, 1'b0};
        end
        else if (south & east) // SE
        begin
            role = `ROLE_BOUNDARY;
            possible_dir = {1'b1, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0};
        end
        else // C
        begin
            role = `ROLE_ACTIVE;
            possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
        end
    end
    //// A
    else if (is_pchtype_a)
    begin
        if (north & west) // NW
        begin
            role = `ROLE_BOUNDARY;
            if (facebd_n == `FACEBD_PP)
                possible_dir = {1'b0, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
            else
                possible_dir = {1'b0, 1'b0, 1'b1, 1'b1, 1'b0, 1'b0};
        end
        else if (north & ~east) // N
        begin
            if (facebd_n == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
            end
            else
            begin
                if (even)
                    role = `ROLE_BOUNDARY;
                else
                    role = `ROLE_ACTIVE;
                possible_dir = {1'b0, 1'b0, 1'b1, 1'b1, 1'b0, 1'b0};
            end
        end
        else if (north & east) // NE
        begin
            if (facebd_n == `FACEBD_PP & facebd_e == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b0, 1'b1, 1'b1, 1'b0, 1'b0};
            end
            else if (facebd_n == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0};
            end
            else if (facebd_e == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b0, 1'b0, 1'b1, 1'b1, 1'b0, 1'b0};
            end
            else
            begin
                role = `ROLE_INACTIVE;
                possible_dir = {1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0};
            end
        end
        else if (west & ~south) // W
        begin
            role = `ROLE_ACTIVE;
            possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
        end
        else if (east & ~south) // E
        begin
            if (facebd_e == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
            end
            else
            begin
                if (even)
                    role = `ROLE_BOUNDARY;
                else
                    role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0};
            end
        end
        else if (west & south) // SW
        begin
            role = `ROLE_ACTIVE;
            possible_dir = {1'b1, 1'b1, 1'b0, 1'b1, 1'b0, 1'b0};
        end
        else if (south & ~east) // S
        begin
            if (facebd_s == `FACEBD_PP)
            begin
                role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
            end
            else
            begin
                if (even)
                    role = `ROLE_BOUNDARY;
                else
                    role = `ROLE_ACTIVE;
                possible_dir = {1'b1, 1'b1, 1'b0, 1'b0, 1'b0, 1'b0};
            end
        end
        else if (south & east) // SE
        begin
            role = `ROLE_BOUNDARY;
            if (facebd_s == `FACEBD_PP & facebd_e == `FACEBD_PP)
                possible_dir = {1'b1, 1'b1, 1'b1, 1'b0, 1'b0, 1'b0};
            else if (facebd_s == `FACEBD_PP)
                possible_dir = {1'b1, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0};
            else if (facebd_e == `FACEBD_PP)
                possible_dir = {1'b1, 1'b1, 1'b0, 1'b0, 1'b0, 1'b0};
            else
                possible_dir = {1'b1, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0};
        end
        else // C
        begin
            role = `ROLE_ACTIVE;
            possible_dir = {1'b1, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0};
        end

    end
    //// invalid
    else 
    begin
        role = `ROLE_INACTIVE;
        possible_dir = {1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0};
    end


    // syn_to_west & syn_to_east
    //// ZT
    if (pchtype == `PCHTYPE_ZT)
    begin
        if (east & (~north) & (~south))
        begin
            if (facebd_e == `FACEBD_MP)
            begin
                if (even)
                begin
                    syn_to_west = `PP_Z;
                    syn_to_east = `PP_X;
                end
                else
                begin
                    syn_to_west = `PP_X;
                    syn_to_east = `PP_Z;
                end
            end
            else
            begin
                if (even)
                begin
                    syn_to_west = `PP_Z;
                    syn_to_east = `PP_I;
                end
                else
                begin
                    syn_to_west = `PP_X;
                    syn_to_east = `PP_I;
                end
            end
        end
        else if (east & south)
        begin
            if (facebd_e == `FACEBD_MP)
            begin
                syn_to_west = `PP_Z;
                syn_to_east = `PP_X;
            end
            else
            begin
                syn_to_west = `PP_Z;
                syn_to_east = `PP_I;
            end
        end
        else
        begin
            if (even)
            begin
                syn_to_west = `PP_Z;
                syn_to_east = `PP_Z;
            end
            else
            begin
                syn_to_west = `PP_X;
                syn_to_east = `PP_X;
            end
        end
    end
    //// MT
    else if (pchtype == `PCHTYPE_MT)
    begin
        if (even)
        begin
            syn_to_west = `PP_X;
            syn_to_east = `PP_X;
        end
        else
        begin
            syn_to_west = `PP_Z;
            syn_to_east = `PP_Z;
        end
    end
    //// OTHERS
    else
    begin
        if (even)
        begin
            syn_to_west = `PP_Z;
            syn_to_east = `PP_Z;
        end
        else
        begin
            syn_to_west = `PP_X;
            syn_to_east = `PP_X;
        end
    end

    //// ZT
    if (pchtype == `PCHTYPE_ZT)
    begin
        if (east) // NE, E, SE
        begin
            if (facebd_e == `FACEBD_MP)
            begin
                if (even)
                    first_aqmeas_flag = 1;
                else
                    first_aqmeas_flag = 0;
            end
            else
            begin
                first_aqmeas_flag = 0;
            end
        end
        else
        begin
            first_aqmeas_flag = 0;
        end
    end
    //// ZB
    else if (pchtype == `PCHTYPE_ZB)
    begin
        if (east) // NE, E, SE
        begin
            if (facebd_e == `FACEBD_PP)
            begin
                if (even)
                    first_aqmeas_flag = 0;
                else
                    first_aqmeas_flag = 1;
            end
            else
            begin
                first_aqmeas_flag = 0;
            end
        end
        else
        begin
            first_aqmeas_flag = 0;
        end
    end
    //// MT
    else if (pchtype == `PCHTYPE_MT)
    begin
        if (facebd_w == `FACEBD_MP) // merge
        begin
            if (north | east) // NW, N, NE, E, SE
            begin
                if (even)
                    first_aqmeas_flag = 1;
                else
                    first_aqmeas_flag = 0;
            end
            else
            begin
                first_aqmeas_flag = 1;
            end
        end
        else // prep, split
        begin
            first_aqmeas_flag = 0;
        end
    end
    //// MB
    else if (pchtype == `PCHTYPE_MB)
    begin
        if ((facebd_n == `FACEBD_LP) & (facebd_w == `FACEBD_PP)) // merge
        begin
            if ((north & even) | (north & east)) // NW, N, NE
            begin
                first_aqmeas_flag = 1;
            end
            else if (west & ~even) // W, SW
            begin
                first_aqmeas_flag = 1;
            end
            else if (east & ~even) // E
            begin
                first_aqmeas_flag = 1;
            end
            else // OTHERS
            begin
                first_aqmeas_flag = 0;
            end
        end
        else // prep, split
        begin
            first_aqmeas_flag = 0;
        end
    end
    //// M
    else if (pchtype == `PCHTYPE_M)
    begin
        if (north & ~even) // NW, N, NE
        begin
            if (facebd_n == `FACEBD_PP)
                first_aqmeas_flag = 1;
            else
                first_aqmeas_flag = 0;
        end
        else if (south & ~even) // SW, S, SE
        begin
            if (facebd_s == `FACEBD_PP)
                first_aqmeas_flag = 1;
            else
                first_aqmeas_flag = 0;
        end
        else // OTHERS
        begin
            first_aqmeas_flag = 0;
        end
    end
    //// X
    else if (pchtype == `PCHTYPE_X)
    begin
        if (west & ~even) // NW, W, SW
        begin
            if (facebd_w == `FACEBD_PP)
                first_aqmeas_flag = 1;
            else
                first_aqmeas_flag = 0;
        end
        else // OTHERS
        begin
            first_aqmeas_flag = 0;
        end
    end
    //// A
    else if (is_pchtype_a)
    begin
        if (north & west) // NW
        begin
            first_aqmeas_flag = 0;
        end
        else if (north & ~east) // N
        begin
            if (facebd_n == `FACEBD_PP)
            begin
                first_aqmeas_flag = 1;
            end
            else
            begin
                if (even)
                    first_aqmeas_flag = 0;
                else
                    first_aqmeas_flag = 1;
            end
        end
        else if (north & east) // NE
        begin
            if ((facebd_n == `FACEBD_PP) | (facebd_e == `FACEBD_PP))
                first_aqmeas_flag = 1;
            else
                first_aqmeas_flag = 0;
        end
        else if (west & ~south) // W
        begin
            first_aqmeas_flag = 1;
        end
        else if (east & ~south) // E
        begin
            if (facebd_e == `FACEBD_PP)
            begin
               first_aqmeas_flag = 1; 
            end
            else
            begin
                if (even)
                    first_aqmeas_flag = 0;
                else
                    first_aqmeas_flag =1;
            end
        end
        else if (west & south) // SW
        begin
            first_aqmeas_flag = 1;
        end
        else if (south & ~east) // S
        begin
            if (facebd_s == `FACEBD_PP)
            begin
                first_aqmeas_flag = 1;
            end
            else
            begin
                if (even)
                    first_aqmeas_flag = 0;
                else
                    first_aqmeas_flag = 1;
            end
        end
        else if (south & east) // SE
        begin
            first_aqmeas_flag = 0;
        end
        else // C
        begin
            first_aqmeas_flag = 1;
        end
    end
    //// invalid
    else 
    begin
        first_aqmeas_flag = 0;
    end
end

endmodule
