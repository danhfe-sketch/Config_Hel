# Progress Dialog Consolidation Requirements

## Overview
The application currently shows two different progress dialogs simultaneously when loading a profile to the device, creating a confusing user experience with inconsistent layouts and themes. This spec addresses consolidating these into a single, consistent progress dialog.

## Problem Statement
When deploying a profile to a device, users see:
1. A light-themed dialog titled "Loading Profile to Device" 
2. A dark-themed dialog titled "Deploy Profile to Device"

Both dialogs show different progress information and layouts, which is confusing and inconsistent with the application's design.

## Requirements

### Requirement 1: Single Progress Dialog

**User Story:** As a user deploying a profile to a device, I want to see only one progress dialog so that I have a clear and consistent view of the operation progress.

#### Acceptance Criteria
1. WHEN I deploy a profile to device THEN the system SHALL display only one progress dialog
2. WHEN the profile deployment starts THEN the system SHALL NOT show multiple overlapping dialogs
3. WHEN the operation is in progress THEN the dialog SHALL remain consistent throughout the entire process

### Requirement 2: Consistent Dialog Layout

**User Story:** As a user, I want the progress dialog to have a consistent layout that matches the rest of the application so that the interface feels cohesive.

#### Acceptance Criteria
1. WHEN the progress dialog is displayed THEN it SHALL use the same theme (dark/light) as the main application
2. WHEN showing progress information THEN the dialog SHALL use consistent fonts, colors, and spacing with other dialogs
3. WHEN displaying progress details THEN the layout SHALL follow the application's design patterns

### Requirement 3: Comprehensive Progress Information

**User Story:** As a user, I want to see detailed progress information in a single dialog so that I understand what's happening during the deployment process.

#### Acceptance Criteria
1. WHEN the deployment is running THEN the dialog SHALL show the current operation step (e.g., "Configuring Device Parameters")
2. WHEN processing parameters THEN the dialog SHALL display the current parameter being processed (e.g., "7/21")
3. WHEN showing progress THEN the dialog SHALL include both a progress bar and percentage completion
4. WHEN the operation progresses THEN the dialog SHALL update the status message to reflect the current activity

### Requirement 4: Proper Dialog Management

**User Story:** As a user, I want the progress dialog to be properly managed so that there are no duplicate or orphaned dialogs.

#### Acceptance Criteria
1. WHEN a profile deployment starts THEN the system SHALL close any existing progress dialogs for the same operation
2. WHEN the operation completes THEN the dialog SHALL close automatically or provide a clear close option
3. WHEN the operation is cancelled THEN the dialog SHALL handle cancellation gracefully
4. WHEN an error occurs THEN the dialog SHALL display the error state clearly

### Requirement 5: Consistent Progress Tracking

**User Story:** As a user, I want to see accurate and consistent progress tracking so that I know how much of the operation is complete.

#### Acceptance Criteria
1. WHEN the deployment starts THEN the progress SHALL begin at 0% and progress logically to 100%
2. WHEN showing step progress THEN the dialog SHALL display both current step and total steps (e.g., "3 / 4")
3. WHEN processing individual parameters THEN the dialog SHALL show parameter-level progress (e.g., "7/21")
4. WHEN the operation completes THEN the progress SHALL reach 100% before showing completion

## Technical Considerations

### Current Implementation Issues
- Multiple progress dialog instances are being created simultaneously
- Different dialog themes and layouts are being used
- Progress information is duplicated across dialogs
- Dialog lifecycle management is inconsistent

### Proposed Solution Approach
1. Identify and consolidate the multiple dialog creation points
2. Standardize on a single progress dialog implementation
3. Ensure consistent theming and layout
4. Implement proper dialog lifecycle management
5. Consolidate progress tracking into a single source of truth

## Success Criteria
- Only one progress dialog is shown during profile deployment
- The dialog has a consistent layout matching the application theme
- Progress information is comprehensive and accurate
- Dialog management is clean with no orphaned instances
- User experience is smooth and professional