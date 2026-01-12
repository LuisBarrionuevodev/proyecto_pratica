import * as React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Modal from '@mui/material/Modal';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';
import { ModalStyle } from '../../../../../styles/TablasStyle';

const BasicModal = () => {
    const [open, setOpen] = React.useState(true);
    const handleClose = () => setOpen(false);

    return (
        <div>
            <Modal
                open={open}
                onClose={handleClose}
                aria-labelledby="modal-modal-title"
                aria-describedby="modal-modal-description"
            >
                <Box sx={ModalStyle}>
                    <IconButton
                        onClick={handleClose}
                        sx={{
                            position: 'absolute',
                            top: 8,
                            right: 8,
                            color: '#000',
                            transition: "box-shadow 0.4s ease",
                            "&:hover": {
                                boxShadow: "0px 6px 6px #0265FF",
                            },
                        }}
                    >
                        <CloseIcon />
                    </IconButton>

                    <Typography
                        id="modal-modal-description"
                        sx={{
                            fontSize: "20px",
                            fontFamily: "tactic sans",
                            fontWeight: 400
                        }}
                    >
                        Actas esperando respuesta del tribunal...
                    </Typography>
                </Box>
            </Modal>
        </div>
    );
}

export default BasicModal;