import matplotlib.pyplot as plt
import pandas as pd

def returns_df(report_dicts, report_titles, normalize=True):
	#Report dicts - must have both 'time' and 'value' keys
	#Report titles - must all be unique

	frames = []
	for i in range(len(report_dicts)):
		rd = report_dicts[i]
		rt = report_titles[i]
		df = pd.DataFrame(rd)
		if normalize:
			df['value'] = df['value']/df['value'][0]
		df =df.rename(columns={'value':rt})
		frames.append(df)

	result = frames[0]
	for frame in frames[1:]:
		result = result.merge(frame, on='time',how='outer')

	return result.set_index('time')

def alpha_df(df, control_col, perform_cols=None, resample='M'):
	#df - dataframe of returns with datetime index (designed for returns_df() )
	#control_col - single column name which contains the control var
	#perform_cols - list of column names for which the alpha is being calculated
	#  default (None) = all columns but control_col
	#remaple - to get annual ('A'), monthly ('M') alpha. 
	#Input is rule for pandas dataframe.resample() method

	df = df.copy() #don't alter original!
	if perform_cols == None:
		perform_cols = [x for x in df.columns if x != control_col]
	for p in perform_cols:
		df[p] = df[p]/df[control_col]

	return df.resample(resample).mean()


