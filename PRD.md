# Product Requirements Document: LT32Pro Device Configurator v1

## 1. Introduction

This document outlines the product requirements for the "LT32Pro Device Configurator v1," a desktop application for Windows 11. This software serves as the primary interface for technicians and administrators to configure, monitor, and manage LT32Pro tracking hardware. It modernizes the existing `LT32Pro Configurator` by introducing an updated user interface, improved usability, and robust features, ensuring a seamless experience on the Windows 11 platform.

**Target Audience:**
*   Field Technicians
*   System Administrators
*   Support Staff

## 2. Vision and Goals

**Vision:** To provide a modern, intuitive, and reliable tool for configuring LT32Pro hardware, improving technician efficiency and reducing configuration errors.

**Business Goals:**
*   Modernize the existing application to align with current UI/UX standards.
*   Ensure compatibility and stability with the Windows 11 operating system.
*   Provide a platform for future feature enhancements.
*   Enable branding and customization options for partners.

**User Goals:**
*   Quickly and easily connect to a device.
*   Clearly view the current device configuration.
*   Modify and send single or multiple configuration parameters reliably.
*   Monitor the device's real-time communication log.
*   Save and load common configuration profiles.
*   Access necessary drivers and manuals directly from the application.

## 3. Target Platform

*   **Operating System:** Windows 11
*   **Framework:** Python with a suitable GUI toolkit (e.g., Tkinter, PyQt, or Kivy).

## 4. Features and Requirements

### 4.1. Core Functionality: Device Management

#### 4.1.1. Serial (COM) Port Communication
*   **Requirement:** The application must automatically detect and list available COM ports.
*   **Requirement:** Users must be able to manually select a COM port from the list.
*   **Requirement:** A clear visual indicator must show the connection status (e.g., Connected/Green, Disconnected/Red).
*   **Requirement:** The application must gracefully handle connection errors (e.g., device unplugged).

#### 4.1.2. Device Configuration
*   **Requirement:** The UI must provide intuitive controls for all device parameters seen in the v3.19 screenshot. This includes:
    *   Numeric inputs (Vibration, Timers, Sensitivity)
    *   Dropdowns (Heart Beat, Curve Sensor)
    *   Radio buttons (Transmission Mode, Lock Type, Ignition Type, Protocol, Timezone)
    *   Text inputs (APN, IP/DNS, Port)
*   **Requirement:** Each parameter must have an "Enviar" (Send) button to update the setting on the device individually.
*   **Requirement:** The application must validate user input to prevent errors (e.g., ensure values are within the specified range).

#### 4.1.3. Bulk Commands & Device Actions
*   **Requirement:** The following global actions must be available as buttons:
    *   **Enviar todos os comandos:** Sends all currently displayed settings to the device.
    *   **Checar configuração:** Reads the current configuration from the device and populates the UI fields.
    *   **Reiniciar equipamento:** Sends a command to reboot the device.
    *   **Reset de fábrica:** Sends a command to restore the device to its factory default settings. A confirmation dialog must be shown before proceeding.

#### 4.1.4. Serial Log & Custom Commands
*   **Requirement:** A dedicated, scrollable text area shall display the real-time serial communication log between the application and the device.
*   **Requirement:** The log must be clear and easy to read, with options to copy or export the log to a text file.
*   **Requirement:** A "Comando Livre" (Free Command) input field and "Enviar" button must be provided for sending custom or diagnostic commands to the device.

### 4.2. User Interface & Experience

#### 4.2.1. Main Window
*   **Requirement:** The application will have a modern, clean UI following Windows 11 design principles (e.g., Mica/Acrylic effects, rounded corners).
*   **Requirement:** The layout will be organized logically, grouping related settings into sections as in the original design.
*   **Requirement:** The application window must be resizable, with content adapting gracefully to different sizes.
*   **Requirement:** The IMEI and ICCID of the connected device should be clearly displayed when available.

#### 4.2.2. Toolbar
*   **Requirement:** A toolbar at the top of the application will provide access to higher-level functions:
    *   **Perfis de Configuração (Configuration Profiles):** Dropdown to save the current settings as a named profile or load a previously saved profile.
    *   **Idioma (Language):** Dropdown to switch the UI language (e.g., Portuguese, English, Spanish).
    *   **Ajuda (Help):** Dropdown with links to:
        *   Install/Update `Driver Cabo de Configuração` (Configuration Cable Driver).
        *   Open `Manuais de Equipamentos` (Equipment Manuals - PDF or web link).
    *   **Restaurar Padrões (Restore Defaults):** Resets the UI fields to the application's default values (not the device's factory settings).
    *   **Personalização (Personalization):** Opens a settings dialog for app customization.

### 4.3. Advanced Features

#### 4.3.1. Configuration Profiles
*   **Requirement:** Users must be able to save the complete set of on-screen configurations as a local file (`.lt32config`).
*   **Requirement:** Users must be able to load a `.lt32config` file to populate the UI instantly.

#### 4.3.2. Internationalization
*   **Requirement:** The application must support multiple languages. At a minimum, Portuguese, English, and Spanish will be included. The default language will be Portuguese.

#### 4.3.3. Customization & Branding
*   **Requirement:** A "Personalization" screen, accessible from the toolbar, will allow users/partners to customize the application's appearance.
*   **Requirement:** The Personalization screen shall provide the following options:
    *   **Theme Selection:**
        *   An option to choose between "Light", "Dark", and "System" themes.
        *   The theme change will be applied instantly without requiring an application restart.
        *   The selected theme will be saved and applied on subsequent launches.

## 5. Non-Functional Requirements

*   **Performance:** The application must be responsive, with no noticeable lag during UI interaction or device communication.
*   **Reliability:** The application must be stable and handle unexpected device disconnections or communication errors without crashing.
*   **Usability:** The tool should be intuitive enough for a new technician to use with minimal training.

## 6. Assumptions and Dependencies

*   The user's system has the necessary permissions to install device drivers (for the configuration cable).
*   The application relies on external libraries specified in `requirements.txt`. These libraries, such as `customtkinter`, `pyserial`, and `pyperclip`, must be installed in the Python environment.
*   The device communicates over a standard serial (COM) port at a default baud rate of 9600.

## 7. Revision History

| Version | Date       | Author(s)          | Changes                                                                                                        |
| :------ | :--------- | :----------------- | :------------------------------------------------------------------------------------------------------------- |
| 1.0.0   | 2023-10-27 | Gemini Code Assist | Initial version of the PRD. Defines core functionality for device connection, configuration, logging, and UI/UX. |
| 1.0.1   | 2023-10-27 | Gemini Code Assist | Added details to Customization & Branding. Added Assumptions and Revision History sections.                      |

## 8. Distribution

*   **Requirement:** The application must be packaged as a single, standalone executable file for Windows 11 (e.g., using PyInstaller or a similar tool). This executable should not require any external dependencies or a separate Python installation on the user's machine.
