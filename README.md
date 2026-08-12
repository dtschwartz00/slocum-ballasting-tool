# slocum-ballasting-tool

Interactive Ballasting Optimizer for Slocum G2 gliders with CTD profile support

Learning to ballast a Slocum Glider as a new pilot is a daunting task. The difference between a correctly ballasted glider and one that cannot resurface could mean the loss of a $300k instrument. RUCOOL at Rutgers University has played a pivotal role in the glider community by creating resources and leading workshops for prospective glider pilots. One such resource is their ballasting spreadsheet — a great tool for experienced pilots, but one that doesn't explain the reasoning behind each step. Using resources from the Glider Microcredential workshop, I built this tool so new pilots can see the "why" behind the numbers. 

This tool runs through the five main steps of ballasting: 
(1) Volume - this volume is provided by Teledyne Marine
(2) Density - the proess of making the glider as dense as the target seawater where it will be deployed, with this tool, you can upload a ctd csv file and it will output an approx glider ballast recommendation based on the CTD profile, DO NOT just trust tool, make sure to actually place in the ballast tank and go through whole process
**GLIDER SHOULD ALWAYS BE IN LAB MODE IN THIS PROCESS**
(3) Trim / Balance - We're checking there is not to much of an imbalance netweem the fore and the aft therefore S1 should be approximately equal to S2
(4) Roll - as you are already in lab mode your roll should be as near zero as possible 
(5) H-Moment - this is our last step, we're taking the calculations of the added weight and the hull radius to find the stabiliy of our ballasted glider  

## Quick Start
git clone https://github.com/YOUR-USERNAME/slocum-ballasting-tool.git
cd slocum-ballasting-tool
pip install -r requirements.txt
streamlit run app.py

## REFERENCES 
Webb, D.C., Simonetti, P.J., Jones, C.P. (2001). SLOCUM: An Underwater Glider Designed for Sustained and Vertical Stability. IEEE Journal of Oceanic Engineering.

Graver, J.G. (2005). Underwater Gliders: Dynamics, Control and Design. PhD Thesis, Princeton University.

Rutgers COOL Glider Microcredential Workshop materials: https://marine.rutgers.edu/~dkaragon/glider_training/mts_17/Glider%20Ballasting%20Template.xls

