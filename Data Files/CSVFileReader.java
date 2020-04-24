package com.dxc;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;  
import java.io.IOException;  

public class CSVFileReader 
{ 
	public static void main(String[] args)   
	{  
		BufferedReader br = null;
		String line = "";  
		String splitBy = ",";

		try   
		{  
			br = new BufferedReader(new FileReader("C:\\IAM\\Test_Data\\testdata-1.csv"));

			while ((line = br.readLine()) != null)   //returns a Boolean value  
			{  
				System.out.println(line);
				line.split(splitBy);    // use comma as separator    
			}  
		}

		catch (IOException e)   
		{  
			e.printStackTrace();  
		}

		try
		{
			File directory = new File("C:\\IAM\\Test_Data\\Archive");
			boolean fileExists = directory.exists();
			
			// Create one directory
			fileExists = directory.mkdir();
			
			if (fileExists != false) 
			{
				System.out.println("Directory : " + directory + " Created...!");
			} 
			
			else
			{
				System.out.println("\nDirectory already exists...!");
			}

		}
		catch (Exception e)
		{
			//Catch exception if any
			System.err.println("Error: " + e.getMessage());
		}

	} 
}
