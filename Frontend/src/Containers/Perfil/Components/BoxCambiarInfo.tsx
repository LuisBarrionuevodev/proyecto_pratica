import { Box, Button, TextField, Typography } from "@mui/material";
import { ButtonGuardarInfoStyle, InputCambiarInfoStyle } from "../../../styles/PerfilStyles";

const BoxCambiarInfo = () => {
    return (
        <Box sx={{ border: "1px solid black", borderRadius: "20px",boxShadow:"6px 6px 2px black" , display: "flex",  height: "450px", flexDirection: "column", alignItems: "center", width: {md:"500px"}, gap: 3, m: 8, p: 3 }}>
            <Box sx={{ display: "flex", alignSelf: "start" }}>
                <Typography sx={{ fontSize: 20, fontWeight: 500, }}>
                    Datos del Perfil
                </Typography>
            </Box>
            <Box>
                <Typography ml={1} fontSize={15} fontWeight={500} >
                    Nombre
                </Typography>
                <TextField placeholder="Nombre" sx={InputCambiarInfoStyle} />
            </Box>

            <Box>
                <Typography ml={1} fontSize={15} fontWeight={500} >
                    Contraseña
                </Typography>
                <TextField placeholder="**********" sx={InputCambiarInfoStyle} />
            </Box>

            <Box>
                <Typography ml={1} fontSize={15} fontWeight={500} >
                    Repetir Contraseña
                </Typography>
                <TextField placeholder="**********" sx={InputCambiarInfoStyle} />
            </Box>

            <Button sx={ButtonGuardarInfoStyle}>
                Guardar Cambios
            </Button>
        </Box>
    )
}

export default BoxCambiarInfo;