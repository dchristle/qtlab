##example1 = qt.instruments.create('example1', 'example', address='GPIB::1', reset=True)
dsgen = qt.instruments.create('dsgen', 'dummy_signal_generator')
pos = qt.instruments.create('pos', 'dummy_positioner')
combined = qt.instruments.create('combined', 'virtual_composite')
combined.add_variable_scaled('magnet', example1, 'chA_output', 0.02, -0.13, units='mT')
ddg = qt.instruments.create('ddg','SR_DG645',address='GPIB0::15::INSTR')
tl = qt.instruments.create('tl','ThorLabs_ITC4001',address='USB0::0x1313::0x804A::M00277475::INSTR')
#combined.add_variable_combined('waveoffset', [{
#    'instrument': dmm1,
#    'parameter': 'ch2_output',
#    'scale': 1,
#    'offset': 0}, {
#    'instrument': dsgen,
#    'parameter': 'wave',
#    'scale': 0.5,
#    'offset': 0
#    }], format='%.04f')
