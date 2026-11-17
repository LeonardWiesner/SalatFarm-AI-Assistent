package VerticalFarming_v1
   
model GlobalConstants
    import Modelica.Units.SI.*;
    constant Temperature T_amb = 273.15;
    constant AbsolutePressure p_amb = 101325;
    constant Density rho_air_amb = 1.2;
    constant SpecificHeatCapacity cp_air = 1005;

    
  end GlobalConstants;

  package Models   
package PartialModels

      model mChannel
      import Modelica.Units.SI.*;
      
      parameter Mass mChannel_0 = 0;
      parameter Length ChannelWidth = 0.1;
      parameter Length ChannelLength = 0.1;
      parameter Length OverflowLevel;
      parameter Real kFlow(unit="m2.5/s") = 1e-3;
      MassFlowRate m_outflow_actual;
      
      
      Mass mChannel(start=mChannel_0, fixed = true);
      
      Connectors.WaterPort inlet;
      Connectors.WaterPort outlet;
      
      
      equation
//Mass balance of Channel
        der(mChannel) = inlet.m_flow + outlet.m_flow;
      
      
      OverflowLevel = mChannel/(Media.Water.rho*ChannelLength*ChannelWidth);
//Channel with numerical flow restriction
      m_outflow_actual = Media.Water.rho*kFlow*sqrt(max(OverflowLevel,0));
      
      
      inlet.h_outflow = outlet.h_outflow;
      
      inlet.p = GlobalConstants.p_amb;
      
      inlet.p = outlet.p;
      
      end mChannel;

      partial model Plant
        import Modelica.Units.SI.*;
        replaceable package Crop = Crops.Salat
        constrainedby Crops.Interfaces.PartialCropData
        annotation(choicesAllMatching = true);
        
        Connectors.LightPort lightport_b;
        /* Lightports connects Plant with GrowLight and transports the Light demand of the plants to the GrowLight via PPFD */
      
          
        parameter input Real n_plants
        "Number of plants";
        
        parameter input Real LUE_set(
        unit="kg/mol")
        "Net dry shoot biomass produced per incident photon amount";
        
        
        /*
         * Cultivation geometry
         *
         * 
         * A_perPlant = cultivation area of one plant.
         *
         * 
         * A_cultivation = total area of all plants.
         */
      
        Area A_cultivation
        "Cultivation area that needs illumination";
      
      
        /*
         * Water demand
         */
      
        parameter Real x_waterConsumption(
          min = 0,
          unit = "1/d") = 0.5
          "Water demand per kg fresh plant mass and day";
      
        /*
         * Input from GrowLight
         *
         * PPFD is represented in SI units:
         * mol/(m2.s), not umol/(m2.s).
         */
      
        /*input Real PPFD(
          min = 0,
          unit = "mol/(m2.s)")
          "Incident photosynthetic photon flux density";
          */       //wird ersetzt durch LightConnector
        /*
                 * Plant masses
                 */
                 
        Mass mDryShoot(
          start = Crop.Ratio_DW*Crop.m_seedlingFresh*n_plants,
          fixed = true)
          "Current shoot dry mass";
      
        Mass mPlant
          "Current shoot fresh mass";
      
        /*
         * Water flows
         */
      
        MassFlowRate m_flow_waterDemand
          "Required water flow";
      
        MassFlowRate m_flow_waterActual
          "Actually absorbed water flow";
      
        Real waterSupplyRatio(
          min = 0,
          max = 1)
          "Fraction of water demand supplied";
          
         Boolean harvestReady
         "Is true when harvesting mass is reached.";
         
         parameter input Boolean stopAtHarvest
         "Terminates simulation when harvesting mass is reached.";
         
      
        /*
         * Growth rates
         */
      
        MassFlowRate growthRateDry
          "Dry shoot mass growth rate";
      
        MassFlowRate growthRate
          "Fresh shoot mass growth rate";
      
        /*
         * Accumulated light
         */
      
        Real cumulativePhotonExposure(
          start = 0,
          fixed = true,
          unit = "mol/m2")
          "Cumulative incident photon amount per cultivation area";
          
        Real f_intercept(min=0, max=1)
        "Fraction of incident light intercepted by crop";
      
        Real LAI(unit="1")
        "Leaf area index";
      
      equation
      
        /*
         * Fresh mass calculated from dry mass.
         * A constant dry matter fraction is assumed.
         */
        A_cultivation = n_plants*Crop.A_perPlant;
        
        /* Required Lumination Area is transported via LightPort*/
        
        lightport_b.A_cultivation = A_cultivation;
      
        /*Calculation of the Fresh mass mPlant with fixed DryWeight ratio.*/
        
        mPlant =
          mDryShoot/Crop.Ratio_DW;
          
        /*Termination of Simulation as soon as the harvesting mass is reached. */
        
     
        harvestReady = mPlant >= n_plants*Crop.m_harvestFresh;
      
        when stopAtHarvest and harvestReady then
          terminate("Harvest mass reached");
        end when;
        
      
        /*
         * Water demand.
         *
         * x_waterConsumption is specified per day,
         * therefore division by 86400 converts it to seconds.
         */
      
        m_flow_waterDemand =
          mPlant*x_waterConsumption/86400;
      
        /*
         * Avoid division by zero and prevent ratios outside 0...1.
         */
      
        waterSupplyRatio =
          if m_flow_waterDemand > Modelica.Constants.small then
            max(
              0,
              min(
                1,
                m_flow_waterActual/m_flow_waterDemand))
          else
            1;
      
        /*
         * Accumulation of incident light.
         *
         * Since PPFD is already zero during the dark period,
         * the photoperiod does not appear separately here.
         */
        
        der(cumulativePhotonExposure) =
          lightport_b.PPFD;
          
          /*Calculation of incident light with a simple model*/
          
          LAI = Crop.SLA*mDryShoot/A_cultivation; //Ratio between leaf area of all plant and cultivation area
          f_intercept = 1 - exp(-Crop.k*LAI); //Beer-Lambert-Light interception

         /*
         * LUE-based net dry-mass production:
         *
         * kg/s =
         * kg/mol * mol/(m2.s) * m2
         *
         * waterSupplyRatio is a simple empirical water-stress factor.
         */
        growthRateDry =
          LUE_set
          * f_intercept
          * lightport_b.PPFD
          * A_cultivation
          * waterSupplyRatio;
      
        der(mDryShoot) =
          growthRateDry;
      
        /*
         * Fresh-mass growth corresponding to the dry-mass growth.
         */
      
        growthRate =
          growthRateDry/Crop.Ratio_DW;
          
        
      
      end Plant;

      
    end PartialModels;
    model PlantUnit
      import Modelica.Units.SI.*;
      extends PartialModels.Plant;
      
      Connectors.WaterPort inlet;
      Connectors.WaterPort outlet;
      
      MassFlowRate m_flow_in
          "Flow entering plant unit";
      
      MassFlowRate m_flow_return
          "Flow returning from plant unit";
          
      Power H_flow_plant
          "Enthalpy flow absorbed with plant water";
          
      SpecificEnthalpy h_in;
          
      
      equation
        /*
         * FluidPort convention:
         * inlet.m_flow > 0 means flow entering PlantUnit.
         */
        m_flow_in = max(0, inlet.m_flow);
// Plant can only absorb as much water as is available
        m_flow_waterActual =
          min(m_flow_waterDemand, m_flow_in);
// Remaining water is returned
        m_flow_return =
          m_flow_in - m_flow_waterActual;
      
        /*
         * At outlet, flow leaving the component has a negative sign
         * because m_flow is defined positive into a component.
         */
      
        outlet.m_flow = -m_flow_return;
//Enthalpy of inlet water
        h_in = inStream(inlet.h_outflow);
//Energy that is absorbed with the plant water
        H_flow_plant = m_flow_waterActual*h_in;
//
          outlet.h_outflow =
          inStream(inlet.h_outflow);
//For possbile reverse flow
        inlet.h_outflow =
          inStream(outlet.h_outflow);
      
        outlet.p = GlobalConstants.p_amb;
        
          assert(
          m_flow_waterActual >= m_flow_waterDemand - 1e-10,
          "Plant receives less water than required.",
          AssertionLevel.warning);
      
      end PlantUnit;

    model Pipe
     import Modelica.Units.SI.*;
    
      parameter Density rho = Media.Water.rho;
      parameter input Height dh;
      parameter input Length L;
      parameter input Diameter D;
      
    
      parameter Real K(unit="Pa.s2/kg2") = 0
        "Hydraulic resistance";
    
      Connectors.WaterPort inlet;
      Connectors.WaterPort outlet;
    
      MassFlowRate m_flow;
      PressureDifference dp_geo;
      PressureDifference dp_friction;
      
      ReynoldsNumber Re;
    
    equation
      inlet.m_flow + outlet.m_flow = 0; //Mass balance
      m_flow = inlet.m_flow;
    
      dp_geo =
        rho*Modelica.Constants.g_n*dh;
//Not-turbulent flow -> Hagen-Poiseuille equation for presssure loss
      dp_friction = (128*Media.Water.eta*L)/(Modelica.Constants.pi*rho*D^4)*m_flow;
    
      inlet.p - outlet.p =
        dp_geo + dp_friction;
        
        outlet.p = GlobalConstants.p_amb;
//For now, no heatloss
      outlet.h_outflow = inStream(inlet.h_outflow);
      inlet.h_outflow = inStream(outlet.h_outflow);
      
      
      Re = rho*abs(m_flow/(rho*Modelica.Constants.pi*D^2/4))*D/Media.Water.eta; //Check if flow is laminar
      assert(Re < 2300, "Flow is no longer laminar.", AssertionLevel.warning);
    
    end Pipe;

    model Pump
      import Modelica.Units.SI.*;
    
      parameter PressureDifference dpShutoff = 150000
        "Pressure increase at zero flow";
    //Maximum MassFlowRate without resistance
      parameter MassFlowRate mFlowMax = 0.5
        "Flow rate at zero pressure increase";
    
      parameter Efficiency eta = 0.8;
    
      Connectors.WaterPort inlet;
      Connectors.WaterPort outlet;
    
      MassFlowRate m_flow;
      PressureDifference dp;
      Power P_hyd;
      Power P_el;
      Energy W_el(
      start = 0,
      fixed = true);
      
      /*Disclaimer for pump function:
      Approximation of pump curve by max VolumeFlowRate and max Pressuredifference,
      for a more precise solution use a specific curve.
      */
      
    
    equation
      inlet.m_flow + outlet.m_flow = 0;
      m_flow = inlet.m_flow;
    
      dp =
        dpShutoff*
        (1 - (m_flow/mFlowMax)^2);
    
      outlet.p - inlet.p = dp;
    
      P_hyd =
        max(0, dp*m_flow/Media.Water.rho);
    
      P_el =
        P_hyd/eta;
        
      der(W_el) = P_el;
//So far no enthalpy change of water is considered
      outlet.h_outflow =
        inStream(inlet.h_outflow);
    
      inlet.h_outflow =
        inStream(outlet.h_outflow);
    
    end Pump;

    model Tank
    import Modelica.Units.SI.*;
    
      parameter input Mass mWater_0;
      parameter input Temperature T_0;
    
      parameter input Area crossArea;
      
    
      Mass mWater(
        start=mWater_0,
        fixed=true);
      
    
    
      Temperature T(
        start=T_0,
        fixed=true);
    
      Energy U(
        start=mWater_0*Media.Water.cp*(T_0 - GlobalConstants.T_amb),
        fixed=true);
    
      Height level;
    
      Connectors.WaterPort inlet;
      Connectors.WaterPort outlet;
    
    equation
      level =
        mWater/(Media.Water.rho*crossArea);
//Tank inlet is above water level
//Calculation of pressure at tank outlet/pump inlet (bottom of tank)
      outlet.p = GlobalConstants.p_amb + Media.Water.rho * Modelica.Constants.g_n * level;
    
      der(mWater) = inlet.m_flow + outlet.m_flow;
      
      
    
      /*
       * Diese Bilanz ist für die vorgesehene Strömungsrichtung:
       * inlet.m_flow > 0 und outlet.m_flow < 0.
       */
      der(U) =
        inlet.m_flow*inStream(inlet.h_outflow)
        + outlet.m_flow*outlet.h_outflow;
    
      U =
        mWater*Media.Water.cp
        *(T - Media.Water.T_ref);
// Wasser verlässt den Tank mit Tanktemperatur
      outlet.h_outflow =
        Media.Water.specificEnthalpy(T);
// Definition für mögliche Rückströmung
      inlet.h_outflow =
        Media.Water.specificEnthalpy(T);
    
      assert(
        mWater >= -1e-6,
        "Tank is empty.");
    end Tank;

    model GrowLight
    import Modelica.Units.SI.*;
      
      Connectors.LightPort lightport_a;
      
      
    parameter Real eta_LED(
    unit = "mol/J")
     = 4.1*0.9e-6 //Reduction by 10% for Humidity protection of lens, Blue-Red LED (highly efficient)
    "Photon Efficacy";
    //Source: https://www.osti.gov/pages/biblio/1624037
    Real PPF(
    unit="mol/s")
    "Photosynthetic Photon Flux";
    
    parameter input Real PPFD_set(
    unit="mol/(m2.s)")
    "Photosynthetic Photon Flux Density";
    
    parameter input Time photoperiod_set
    "Recommended lighting duration per day";
    
    Real PPFD_actual(
    unit="mol/(m2.s)")
    "Photosynthetic Photon Flux Density Actual";
    
    parameter Real f_opt = 0.75
    "Fraction of fixture PPF reaching the cultivation area";     //Source: assumption by chat, to be checked
    Power P_el
    "Required electrical Power by PPFD";
    
    Power P_el_actual
    "Actual electrical Power";
    
    Power Q_GrowLight
    "Heat generated by GrowLight";
    
    Energy W_el(
    start = 0,
    fixed = true)
    "Energy consumed by GrowLight";
    
    
    
      input Real control(min=0, max=1) = 1
        "Lamp power modulation during lighting period";
        
       Boolean lightOn
        "True while the lamp is scheduled to operate";
    
    
      Real effectiveControl(min=0, max=1);
    
    
    equation
      
      der(W_el) = P_el_actual;
    
      lightOn = mod(time, 24*3600) < photoperiod_set; //From simulation start to 16h
      effectiveControl = 
      if lightOn then control else 0;
      
      P_el_actual = P_el * effectiveControl;
      
      PPFD_actual = PPFD_set * effectiveControl;
      
     PPF = eta_LED*P_el;
     
     PPFD_set = f_opt * eta_LED * P_el / lightport_a.A_cultivation;
     
     Q_GrowLight = P_el_actual; //Nearly all power is converted to heat
//Mögliche Erweiterungen: Tageslicht, Actual und Optimal PPFD, Abstand zw. Pflanze und Lampe, Verschattung durch wachsende Blätter
//Hohe PPFD verkürzt erntezeit aber photosynthese weniger effizient -> LUE geht runter
//Denkanstoß für Regelungstechnik der gesamten Anlage: https://ifatwww.et.uni-magdeburg.de/ifac2020/media/pdfs/0405.pdf
//Kurve aus Experimenten für Salat um Optimum zwischen PPFD vs LUE/Erntezeit zu ermitteln -> Ansatz zur Optimierung mit Python
/* PPFD 200 -> LUE 1,01  -> in 26 days
        PPFD 400 -> LUE 0,87  -> in 20 days
        PPFD 750 -> LUE 0,76  -> in 18 days
        */
     lightport_a.PPFD = PPFD_actual;
    end GrowLight;

    model ClimateRoom
    import Modelica.Units.SI.*;
    
    parameter Volume V_air = 25
    "Volume of Grow room";
    
    HeatCapacity C_room
    "Effective heat capacity of room air";
    
    
    
    equation

    end ClimateRoom;
  end Models;



  package Connectors
   
connector WaterPort
      import Modelica.Units.SI.*;
      AbsolutePressure p "Pressure";
      flow MassFlowRate m_flow "Mass flow rate, positive into component";
      stream SpecificEnthalpy h_outflow "Specific enthalpy of fluid leaving component";
    end WaterPort;

    connector LightPort
    
    Real PPFD(
    unit="mol/(m2.s)")
    "Photosynthetic Photon Flux Density Actual";
    
    Modelica.Units.SI.Area A_cultivation
    "Area that requires illumination";
    
    
    end LightPort;
  end Connectors;

  package Media
  package Water
  import Modelica.Units.SI.*;
  
    constant Density rho = 1000;
    constant SpecificHeatCapacity cp = 4180;
    constant Temperature T_ref = 273.15;
    constant DynamicViscosity eta = 1e-3;
  
    function specificEnthalpy
      input Temperature T;
      output SpecificEnthalpy h;
      
    algorithm
      h := cp*(T - T_ref);
    end specificEnthalpy;
  
    function temperature //T in K
      input SpecificEnthalpy h;
      output Temperature T;
    algorithm
      T := T_ref + h/cp;
      
  end temperature;
  end Water;
  end Media;

  model Systemmodel
  
  /* The Model contains 5 Models: Tank, Pipe, Plantunit, Pump and GrowLight. The Tank contains water for the plants.
    The Pipe connects the Pump with the Plantunit and restricts the flow. The Plantunit contains the Plants is connected with the GrowLight via a Lightport that transmits the Area and PPFD required to grow the plants. */
    
  parameter Real LUE_set(
    unit="kg/mol") = Crops.Salat.LUE_default
    "Net dry shoot biomass produced per incident photon amount";
    
    parameter  Real PPFD_set(
  unit="mol/(m2.s)")=Crops.Salat.PPFD_default
  "Photosynthetic Photon Flux Density";
  
  parameter Modelica.Units.SI.Time photoperiod_set = Crops.Salat.photoperiod_default
  "Recommended lighting duration per day";
    
  parameter Boolean stopAtHarvest = true
  "If true, simulation terminates once harvesting mass is reached";
  
  parameter Real nPlants = 25
  "Number of plants";
  
  
  Models.Tank tank(mWater_0 = 1000, T_0  =293.15, crossArea = 1);
  Models.Pipe pipe(dh = 10, L = 30, D = 0.05);
  Models.PlantUnit plantunit(
      redeclare package Crop = Crops.Salat, n_plants = nPlants, LUE_set = LUE_set, stopAtHarvest = stopAtHarvest);
  Models.Pump pump;
  Models.GrowLight lettuceLight(
      PPFD_set = PPFD_set, photoperiod_set = photoperiod_set);
  
  
  
  equation
  connect(tank.outlet, pump.inlet);
  connect(pump.outlet, pipe.inlet);
  connect(pipe.outlet, plantunit.inlet);
  connect(plantunit.outlet, tank.inlet);
  
  connect(lettuceLight.lightport_a, plantunit.lightport_b);
  
  
  end Systemmodel;

  package Crops
  
    package Interfaces 
    
      package PartialCropData
      
        constant Real PPFD_default(
        unit="mol/(m2.s)")
        "Optimal Photosynthetic Photon Flux Density"; 
        
        constant Real LUE_default(
        unit="kg/mol")
        "Net dry shoot biomass produced per incident photon amount";
        
        constant Modelica.Units.SI.Time photoperiod_default
        "Recommended lighting duration per day";
        
        constant Real Ratio_DW(
        unit="kg/kg")
        "Fraction of dry mass";
        
        constant Modelica.Units.SI.Mass m_seedlingFresh
        "Fresh mass of one transplant seedling";
        
        constant Modelica.Units.SI.Mass m_harvestFresh
        "Target harvest fresh mass per plant";
        
        constant Modelica.Units.SI.Area A_perPlant
        "Cultivation area required per mature plant";
        
        constant Real k
        "Light extinction coefficient";
      
        constant Real SLA(unit="m2/kg")
        "Specific leaf area";
        
    end PartialCropData;
    
    end Interfaces;
        
  
  package Salat
  extends Interfaces.PartialCropData(
  //Source: https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2020.592171/full
      PPFD_default = 200e-6,   //Highest efficiency PPFD for Salat
      LUE_default = 1.23e-3,   
      photoperiod_default = 16*3600,
      Ratio_DW = 0.028,
      m_seedlingFresh = 0.001,
      m_harvestFresh = 0.25,
      A_perPlant = 0.04,
      k = 0.5,
      SLA = 44.4);
    end Salat;
    
   package Basil //This is just as example, no real data!
      extends Interfaces.PartialCropData(
        PPFD_opt = 350e-6,
        LUE = 0.8e-3,
        photoperiod = 18*3600,
        Ratio_DW = 0.035,
        m_seedlingFresh = 0.001,
       m_harvestFresh = 0.15,
       A_perPlant = 0.0625);
    end Basil;
  end Crops;
end VerticalFarming_v1;
