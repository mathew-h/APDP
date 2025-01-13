# All Purpose Data Processing

#### ** WIP **
#### Description:

## Summary
This project takes battery test files and will pass their contents through an extract, transform, calculate and load pipeline. The vision is to centralize data processing in one project, with the logic for calculations being distributed through source code located in the calculators and utils python files. Role termination led to this project pausing in place, so further development is to be completed for functionality for cycle, formation, HPPC, GITT, EIS, and rate test data formats and test types. Functionality is implemented for intermittent current interrupt test data with file output from Solartron potentiostat in .mdat ZIP file format. 


### File Processor Class
Requests the user to select data files.

### Data Processor Class
Passes transformed data files through series of utils and calculations to draw meaningful insights. 
