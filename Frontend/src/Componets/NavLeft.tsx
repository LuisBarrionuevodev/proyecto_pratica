import { useMemo, useState } from "react";
import {
    Box,
    Drawer,
    List,
    ListItem,
    ListItemButton,
    ListItemIcon,
    ListItemText,
    IconButton,
    Typography,
    Tooltip,
} from "@mui/material";
import KeyboardDoubleArrowRightIcon from "@mui/icons-material/KeyboardDoubleArrowRight";
import KeyboardDoubleArrowLeftIcon from "@mui/icons-material/KeyboardDoubleArrowLeft";
import CloseIcon from "@mui/icons-material/Close";
import { useNavigate, useLocation } from "react-router-dom";
import {
    StyleDrawer,
    StyleDrawerTemporary,
    StyleMobileNavCloseButton,
    StyleListItems,
    StyleListItemsIcon,
    StyleListItem,
    StyleListItemButton,
    StyleListItemText,
    StyleExpandButton,
    StyleSectionHeader,
    StyleLogoutContainer,
    StyleLogoutButton,
} from "../styles/NavBarStyles";
import { logoutItem } from "../constants/menuItems";
import { getVisibleMenuSections } from "../auth/accessConfig";
import { useAppSession } from "../auth/AppSessionProvider";
import { FONT_FAMILY_UI } from "../theme/typography";

export type MobileNavDrawerControl = {
    open: boolean;
    onClose: () => void;
};

interface NavLeftProps {
    onToggle?: (open: boolean) => void;
    /** En móvil: drawer temporal superpuesto en lugar del sidebar permanente. */
    mobileTemporary?: MobileNavDrawerControl;
}

const NavLeft: React.FC<NavLeftProps> = ({ onToggle, mobileTemporary }) => {
    const navigate = useNavigate();
    const location = useLocation();
    const [open, setOpen] = useState(false);
    const { status, role } = useAppSession();

    const isMobileOverlay = Boolean(mobileTemporary);
    const menuExpanded = isMobileOverlay ? true : open;

    const visibleSections = useMemo(() => {
        if (status !== "ready" || !role) return [];
        return getVisibleMenuSections(role);
    }, [status, role]);

    const isActive = (path: string) => location.pathname === path;

    const handleNavigate = (path: string) => {
        navigate(path);
        mobileTemporary?.onClose();
    };

    const menuBody = (
        <>
            {isMobileOverlay ? (
                <IconButton
                    onClick={mobileTemporary?.onClose}
                    aria-label="Cerrar menú de navegación"
                    sx={StyleMobileNavCloseButton}
                >
                    <CloseIcon />
                </IconButton>
            ) : (
                <IconButton
                    onClick={() => {
                        const next = !open;
                        setOpen(next);
                        onToggle?.(next);
                    }}
                    sx={StyleExpandButton}
                >
                    {open ? <KeyboardDoubleArrowLeftIcon /> : <KeyboardDoubleArrowRightIcon />}
                </IconButton>
            )}

            <List sx={StyleListItems(menuExpanded)}>
                {status === "loading"
                    ? null
                    : visibleSections.map((section) => (
                          <Box key={section.label}>
                              <Typography sx={StyleSectionHeader(menuExpanded)}>
                                  {section.label}
                              </Typography>
                              {section.items.map(({ text, icon, path }) => {
                                  const active = isActive(path);
                                  return (
                                      <Tooltip
                                          key={text}
                                          title={!menuExpanded ? text : ""}
                                          placement="right"
                                          arrow
                                      >
                                          <ListItem disablePadding sx={StyleListItem(menuExpanded)}>
                                              <ListItemButton
                                                  onClick={() => handleNavigate(path)}
                                                  sx={StyleListItemButton(menuExpanded, active)}
                                              >
                                                  <ListItemIcon
                                                      sx={StyleListItemsIcon(menuExpanded, active)}
                                                  >
                                                      {icon}
                                                  </ListItemIcon>
                                                  <ListItemText
                                                      primary={text}
                                                      sx={StyleListItemText(menuExpanded, active)}
                                                  />
                                              </ListItemButton>
                                          </ListItem>
                                      </Tooltip>
                                  );
                              })}
                          </Box>
                      ))}
            </List>

            <Box sx={StyleLogoutContainer(menuExpanded)}>
                <Tooltip title={!menuExpanded ? logoutItem.text : ""} placement="right" arrow>
                    <ListItemButton
                        onClick={() => handleNavigate(logoutItem.path)}
                        sx={StyleLogoutButton(menuExpanded)}
                    >
                        <ListItemIcon
                            sx={{
                                color: "#FF6B6B",
                                minWidth: 0,
                                marginRight: menuExpanded ? 1.5 : 0,
                                justifyContent: "center",
                            }}
                        >
                            {logoutItem.icon}
                        </ListItemIcon>
                        <ListItemText
                            primary={logoutItem.text}
                            sx={{
                                opacity: menuExpanded ? 1 : 0,
                                transition: "opacity 0.2s ease",
                                "& .MuiTypography-root": {
                                    color: "#FF6B6B",
                                    fontFamily: FONT_FAMILY_UI,
                                    fontSize: "13px",
                                    fontWeight: 600,
                                },
                            }}
                        />
                    </ListItemButton>
                </Tooltip>
            </Box>
        </>
    );

    if (isMobileOverlay) {
        return (
            <Drawer
                variant="temporary"
                anchor="left"
                open={mobileTemporary?.open ?? false}
                onClose={() => mobileTemporary?.onClose()}
                ModalProps={{ keepMounted: true }}
                sx={StyleDrawerTemporary}
            >
                {menuBody}
            </Drawer>
        );
    }

    return (
        <Box>
            <Drawer variant="permanent" open={open} sx={StyleDrawer(open)}>
                {menuBody}
            </Drawer>
        </Box>
    );
};

export default NavLeft;
