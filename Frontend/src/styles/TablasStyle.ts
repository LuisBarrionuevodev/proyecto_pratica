import { keyframes } from "@emotion/react";

export const TableGeneralStyles = {
    width: { xs: "250px", sm: "500px", md: "900px", lg: "900px", xl: "1200px" },
    display: "flex",
    position: "absolute",
    top: { xs: "10px", sm: "1%", md: "5%", lg: "5%", xl: "10%" },
    marginLeft: { xs: "90px", sm: "100px", md: "100px", lg: "120px", xl: "100px" },
    textAlign: "center",
    justifySelf: "center",
    flexDirection: "column",
    paddingBottom: "20px"
}

export const TableTitleStyles = {
    fontFamily: "tactic sans",
    fontWeight: 800,
    fontSize: { xs: "20px", sm: "35px", md: "50px" }
}

export const TableExportBoxStyles = {
    display: "flex", 
    gap: "10px", 
    padding: "10px", 
    flexDirection:{xs:"column", md: "row"},
}

export const TableExportButtonStyles = {
    fontFamily: "Tactic Sans",
    textTransform: "none",
    fontSize:{xs:"12px",sm:"14px"},
    color: "#0166FF"
}

const shadowFade = keyframes`
  0% {
    text-shadow: 0px 0px 0px rgba(5, 60, 255, 0);
  }
  100% {
    text-shadow: 4px 4px 40px rgba(5, 60, 255, 1);
  }
`;

export const TableLoadingStyles = {
  display: "flex",
  fontFamily: "Tactic Sans",
  fontSize: {xs: "25px", md:"32px"},
  fontWeight: 800,
  animation: `${shadowFade} 0.8s ease-in-out infinite alternate`,
  justifyContent: "center",
  marginTop: "20%",
  marginLeft: {xs:"30%", md:"0%"},
}

export const ModalStyle = {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    width: {xs: 300, md:600},
    bgcolor: 'white',
    border: '2px solid #000',
    boxShadow: 24,
    borderRadius: "25px",
    p: 4,
};



