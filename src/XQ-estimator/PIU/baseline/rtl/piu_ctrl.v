`include "define.v"

module piu_ctrl(
    state,
    pdu_valid,
    next_pchidxsrc,
    pchidx,
    opcode_reg,
    opcode,
    take_in,
    update_pchidxsrc,
    sel_pchidxsrc,
    topsu_valid,
    tolmu_valid,
    next_state,
    is_writing,
    prep_dyninfo,
    split_dyninfo,
    set_merged,
    copy_merged,
    last_pchinfo, 
    pchlist_wren,
    esmon_wren,
    mgdreg_wren,
    mgdmem_wren
);

input [1:0] state;
input pdu_valid;
input [`NUM_PCH-1:0] next_pchidxsrc;
input [`PCHADDR_BW-1:0] pchidx;
input [`OPCODE_BW-1:0] opcode_reg;
input [`OPCODE_BW-1:0] opcode;
output reg take_in;
output reg update_pchidxsrc;
output reg [1:0] sel_pchidxsrc;
output reg topsu_valid;
output reg tolmu_valid;
output reg [1:0] next_state;
output reg is_writing;
output reg prep_dyninfo;
output reg split_dyninfo;
output reg set_merged;
output reg copy_merged;
output reg last_pchinfo;
output reg pchlist_wren;
output reg esmon_wren;
output reg mgdreg_wren;
output reg mgdmem_wren;

always @(*)
begin
    // take_in
    if (state == `PIU_READY | state == `PIU_RESETTING)
    begin
        if (pdu_valid)
            take_in = 1;
        else
            take_in = 0;
    end
    else // READING|WRITING
    begin
        if (pdu_valid & next_pchidxsrc == 0)
            take_in = 1;
        else
            take_in = 0;
    end
    // update_pchidxsrc
    if ((state == `PIU_READING | state == `PIU_WRITING) & (next_pchidxsrc != 0))
        update_pchidxsrc = 1;
    else
        update_pchidxsrc = 0;
    // sel_pchidxsrc, topsu_valid, tolmu_valid
    if (state == `PIU_READING)
    begin
        case (opcode_reg)
            `LQI_OPCODE:
            begin
                if (pchidx == 1) // masking MT
                begin
                    sel_pchidxsrc = `PCHIDXSRC_PCHLIST;
                    topsu_valid = 0;
                    tolmu_valid = 0;
                end
                else
                begin
                    sel_pchidxsrc = `PCHIDXSRC_PCHLIST;
                    topsu_valid = 1;
                    tolmu_valid = 0;
                end
            end
            `LQM_X_OPCODE:
            begin
                sel_pchidxsrc = `PCHIDXSRC_PCHLIST;
                topsu_valid = 1;
                tolmu_valid = 1;
            end
            `LQM_Z_OPCODE:
            begin
                sel_pchidxsrc = `PCHIDXSRC_PCHLIST;
                topsu_valid = 1;
                tolmu_valid = 1;
            end
            `LQM_Y_OPCODE:
            begin
                sel_pchidxsrc = `PCHIDXSRC_PCHLIST;
                topsu_valid = 1;
                tolmu_valid = 1;
            end
            `RUN_ESM_OPCODE:
            begin
                sel_pchidxsrc = `PCHIDXSRC_ESMON;
                topsu_valid = 1;
                tolmu_valid = 0;
            end
            `INIT_INTMD_OPCODE:
            begin
                sel_pchidxsrc = `PCHIDXSRC_MERGED;
                topsu_valid = 1;
                tolmu_valid = 0;
            end
            `MEAS_INTMD_OPCODE:
            begin
                sel_pchidxsrc = `PCHIDXSRC_MERGED;
                topsu_valid = 1;
                tolmu_valid = 0;
            end
            `PPM_INTERPRET_OPCODE:
            begin
                sel_pchidxsrc = `PCHIDXSRC_MERGED;
                topsu_valid = 0;
                tolmu_valid = 1;
            end
            default:
            begin
                sel_pchidxsrc = `PCHIDXSRC_INVALID;
                topsu_valid = 0;
                tolmu_valid = 0;
            end
        endcase
    end
    else if (state == `PIU_WRITING)
    begin
        sel_pchidxsrc = `PCHIDXSRC_MERGED;
        topsu_valid = 0;
        tolmu_valid = 0;
    end
    else
    begin
        sel_pchidxsrc = `PCHIDXSRC_INVALID;
        topsu_valid = 0;
        tolmu_valid = 0;
    end
    // next_state
    if (state == `PIU_READY | state == `PIU_RESETTING)
    begin
        if (pdu_valid)
        begin
            case (opcode)
                `MERGE_INFO_OPCODE:
                    next_state = `PIU_WRITING;
                `PREP_INFO_OPCODE:
                    next_state = `PIU_RESETTING;
                `SPLIT_INFO_OPCODE:
                    next_state = `PIU_RESETTING;
                default:
                    next_state = `PIU_READING;
            endcase
        end
        else
            next_state = `PIU_READY;
    end
    else // READING | WRITING
    begin
        if (next_pchidxsrc == 0)
        begin
            if (pdu_valid)
            begin
                case (opcode)
                    `MERGE_INFO_OPCODE:
                        next_state = `PIU_WRITING;
                    `PREP_INFO_OPCODE:
                        next_state = `PIU_RESETTING;
                    `SPLIT_INFO_OPCODE:
                        next_state = `PIU_RESETTING;
                    default:
                        next_state = `PIU_READING;
                endcase
            end
            else
                next_state = `PIU_READY;
        end
        else
            next_state = state;
    end
    // is_writing
    if (state == `PIU_WRITING)
        is_writing = 1;
    else
        is_writing = 0;
    // prep_dyninfo
    if (state == `PIU_RESETTING & opcode_reg == `PREP_INFO_OPCODE)
        prep_dyninfo = 1;
    else
        prep_dyninfo = 0;
    // split_dyninfo
    if (state == `PIU_RESETTING & opcode_reg == `SPLIT_INFO_OPCODE)
        split_dyninfo = 1;
    else
        split_dyninfo = 0;
    // set_merged
    if (take_in & opcode == `MERGE_INFO_OPCODE)
        set_merged = 1;
    else
        set_merged = 0;
    // copy_merged 
    if (take_in & (opcode == `INIT_INTMD_OPCODE | opcode == `MEAS_INTMD_OPCODE | opcode == `PPM_INTERPRET_OPCODE))
        copy_merged = 1;
    else
        copy_merged = 0;
    // last_pchinfo
    if (state == `PIU_READING & next_pchidxsrc == 0)
        last_pchinfo = 1;
    else
        last_pchinfo = 0;
    // pchlist_wren
    if (take_in | (update_pchidxsrc & sel_pchidxsrc == `PCHIDXSRC_PCHLIST))
        pchlist_wren = 1;
    else
        pchlist_wren = 0;
    // esmon_wren
    if ((prep_dyninfo | split_dyninfo | set_merged) | (update_pchidxsrc & sel_pchidxsrc == `PCHIDXSRC_ESMON))
        esmon_wren = 1;
    else
        esmon_wren = 0;
    // mgdreg_wren
    if ((prep_dyninfo | split_dyninfo | set_merged | copy_merged) | (update_pchidxsrc & sel_pchidxsrc == `PCHIDXSRC_MERGED))
        mgdreg_wren = 1;
    else
        mgdreg_wren = 0;
    // mgdmem_wren 
    if (prep_dyninfo | split_dyninfo | set_merged)
        mgdmem_wren = 1;
    else
        mgdmem_wren = 0;
end

endmodule
