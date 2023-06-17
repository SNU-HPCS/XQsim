`include "define.v"

module pfu_cwdgen( 
    qbidx,
    ucrow, 
    uccol,
    pchinfo_valid, 
    pchtype,
    pchdyn, 
    cwd_opcode,
    cwd_valid,
    cwd_pf
);

input [`QBADDR_BW-1:0] qbidx;
input [`UCADDR_BW-1:0] ucrow, uccol;
input pchinfo_valid;
input [`PCHTYPE_BW-1:0] pchtype;
input [`PCHDYN_BW-1:0] pchdyn;
input [`OPCODE_BW-1:0] cwd_opcode;
input cwd_valid;
output reg [`CWD_BW-1:0] cwd_pf;

wire uc_west = (uccol == 0);
wire uc_north = (ucrow == 0);
wire uc_south = (ucrow == `NUM_UCROW-1);

// wires
wire [`FACEBD_BW-1:0] facebd_w, facebd_n, facebd_e, facebd_s;
wire [`CORNERBD_BW-1:0] cornerbd_nw, cornerbd_ne, cornerbd_sw, cornerbd_se;
assign {facebd_w, facebd_n, facebd_e, facebd_s, cornerbd_nw, cornerbd_ne, cornerbd_sw, cornerbd_se} = pchdyn;

wire anc_pchtype;
assign anc_pchtype = (pchtype == `PCHTYPE_AW | pchtype == `PCHTYPE_AC | pchtype == `PCHTYPE_AE | pchtype == `PCHTYPE_AWE);

reg mask;

always @(*)
begin
    // mask generation
    if (~pchinfo_valid | ~cwd_valid)
    begin
        mask = 0;
    end
    else
    begin
        // for LQI & LQM
        if (cwd_opcode == `LQI_OPCODE | cwd_opcode == `LQM_X_OPCODE | cwd_opcode == `LQM_Y_OPCODE | cwd_opcode == `LQM_Z_OPCODE)
        begin
            if (cwd_opcode == `LQI_OPCODE & pchtype == `PCHTYPE_MT)
            begin
                mask = 0;
            end
            else
            begin
                if (uc_west & uc_north) // NW
                begin
                    if (facebd_n == `FACEBD_PP) // only for ZB
                    begin
                        mask = (qbidx == 1 | qbidx == 3);
                    end
                    else // others
                    begin
                        if (cornerbd_nw != `CORNERBD_C)
                            mask = (qbidx == 3);
                        else
                            mask = 0;
                    end
                end
                else if (uc_north) // N, NE
                begin
                    if (facebd_n == `FACEBD_PP) // only for ZB
                    begin
                        mask = 1;
                    end
                    else // others
                    begin
                        mask = (qbidx == 2 | qbidx == 3);
                    end
                end
                else if (uc_west) // W, SW
                begin
                    if (uc_south & cornerbd_sw == `CORNERBD_C) // only for ZB
                    begin
                        mask = (qbidx == 1);
                    end
                    else // others
                    begin
                        mask = (qbidx == 1 | qbidx == 3);
                    end
                end
                else // C, E, S, SE
                begin
                    mask = 1;
                end
            end
        end
        // for INIT_INTMD & MEAS_INTMD
        else if (cwd_opcode == `INIT_INTMD_OPCODE | cwd_opcode == `MEAS_INTMD_OPCODE)
        begin
            if (uc_west & uc_north) // NW
            begin
                if (qbidx == 0)
                begin
                    mask = 0;
                end
                else if (qbidx == 1)
                begin
                    mask = (facebd_n == `FACEBD_PP & pchtype != `PCHTYPE_ZB);
                end
                else if (qbidx == 2)
                begin
                    mask = (facebd_w == `FACEBD_MP | facebd_w == `FACEBD_PP);
                end
                else // qbidx == 3
                begin
                    if (cwd_opcode == `INIT_INTMD_OPCODE)
                        mask = (pchtype == `PCHTYPE_MT | anc_pchtype);
                    else // MEAS_INTMD
                        mask = anc_pchtype;
                end
            end
            else if (uc_north) // N, NE
            begin
                if (qbidx == 0 | qbidx == 1) 
                begin
                    mask = (facebd_n == `FACEBD_PP & pchtype != `PCHTYPE_ZB);
                end
                else // qbidx == 2 or 3
                begin
                    if (cwd_opcode == `INIT_INTMD_OPCODE)
                        mask = (pchtype == `PCHTYPE_MT | anc_pchtype);
                    else // MEAS_INTMD
                        mask = anc_pchtype;
                end
            end
            else if (uc_west) // W, SW
            begin
                if (qbidx == 1 | qbidx == 3)
                begin
                    if (cwd_opcode == `INIT_INTMD_OPCODE)
                        mask = (pchtype == `PCHTYPE_MT | anc_pchtype);
                    else // MEAS_INTMD
                        mask = anc_pchtype;
                end
                else // qbidx == 0 or 2
                begin
                    mask = (facebd_w == `FACEBD_MP | facebd_w == `FACEBD_PP);
                end
            end
            else // C, E, S, SE
            begin
                if (cwd_opcode == `INIT_INTMD_OPCODE)
                    mask = (pchtype == `PCHTYPE_MT | anc_pchtype);
                else // MEAS_INTMD
                    mask = anc_pchtype;
            end
        end
        // Others: Invalid
        else
        begin
            mask = 0;
        end
    end

    // cwd_pf generation
    if (mask)
    begin
        if (cwd_opcode == `LQI_OPCODE | cwd_opcode == `INIT_INTMD_OPCODE)
            cwd_pf =`CWD_CX;
        else if (cwd_opcode == `LQM_X_OPCODE | cwd_opcode == `LQM_Z_OPCODE | cwd_opcode == `MEAS_INTMD_OPCODE)
            cwd_pf =`CWD_H;
        else if (cwd_opcode == `LQM_Y_OPCODE)
            cwd_pf =`CWD_SDH;
        else
            cwd_pf =`CWD_I;
    end
    else
    begin
        cwd_pf = `CWD_I;
    end
end

endmodule
